import random
import discord
from discord.ext import commands
import json
import os
import requests
from currency_converter import CurrencyConverter


c = CurrencyConverter()

os.chdir(r'C:\Users\mvenkatesh\OneDrive - North Allegheny School District\Documents\hacknaproj')
client = commands.Bot(command_prefix = 'e!', intents=discord.Intents.all())

#remove the default help command
client.remove_command('help')


@client.event
async def on_ready():
    print('Bot is ready.')
    await client.change_presence(activity=discord.Game(name="e!help"))


@client.command()
async def balance(ctx):
    await open_account(ctx.author)
    
    users = await get_bank_data()
    wallet_amt = users[str(ctx.author.id)]["wallet"]
    bank_amt = users[str(ctx.author.id)]["bank"]
    currency = users[str(ctx.author.id)]["currency"]

    embed = discord.Embed(title = f"{ctx.author.name}'s balance", color = discord.Color.red())
    embed.add_field(name = "Wallet", value = wallet_amt)
    embed.add_field(name = "Bank", value = bank_amt)
    embed.add_field(name = "Currency", value = currency)
    await ctx.send(embed = embed)


@client.command()
async def beg(ctx):
    await open_account(ctx.author)
    users = await get_bank_data()
    earnings = random.randrange(10)
    currency = users[str(ctx.author.id)]["currency"]
    earninginamt = c.convert(earnings, 'USD', currency)
    await ctx.send(f"Someone gave you {earnings} {currency}!!")
    users[str(ctx.author.id)]["wallet"] += earnings
    with open('bank.json', 'w') as f:
        json.dump(users, f)

@client.command()
async def help(ctx):
    embed = discord.Embed(title = "Help", description = "Use e! before every command.", color = discord.Color.red())
    embed.add_field(name = "balance", value = "Shows your balance.")
    embed.add_field(name = "beg", value = "Beg for money.")
    embed.add_field(name = "withdraw [amount]", value = "Withdraw money from your bank.")
    embed.add_field(name = "deposit [amount]", value = "Deposit money into your bank.")
    embed.add_field(name = "send [user] [amount]", value = "Send money to someone (different currency = 1% fee)")
    embed.add_field(name = "slots", value = "Play slots.")
    embed.add_field(name = "changecur", value = "Convert your money to another currency with a 1% fee.")
    embed.add_field(name = "curconvert", value = "Get the most recent currency exchange rates.")
    await ctx.send(embed = embed)




@client.command()
async def withdraw(ctx, amount = None):
    await open_account(ctx.author)
    if amount == None:
        await ctx.send("Please enter the amount you want to withdraw.")
        return
    bal = await update_bank(ctx.author)
    currency = bal[2]
    amount = int(amount)
    if amount > bal[1]:
        await ctx.send("You don't have enough money in your bank.")
        return
    if amount < 0:
        await ctx.send("You can't withdraw negative money.")
        return
    await update_bank(ctx.author, amount)
    await update_bank(ctx.author, -1 * amount, "bank")
    await ctx.send(f"You withdrew {amount} {currency}.")


@client.command()
async def deposit(ctx, amount = None):
    await open_account(ctx.author)
    if amount == None:
        await ctx.send("Please enter the amount you want to deposit.")
        return
    bal = await update_bank(ctx.author)
    currency = bal[2]
    amount = int(amount)
    bal2 = await update_bank(ctx.author)
    currency2 = bal2[2]
    if amount > bal[0]:
        await ctx.send("You don't have enough money in your wallet.")
        return
    if amount < 0:
        await ctx.send("You can't deposit negative money.")
        return
    await update_bank(ctx.author, -1 * amount)
    await update_bank(ctx.author, amount, "bank")
    await ctx.send(f"You deposited {amount} {currency}.")

@client.command()
async def send(ctx, member: discord.Member, amount = None):
    await open_account(ctx.author)
    await open_account(member)
    if amount == None:
        await ctx.send("Please enter the amount you want to send.")
        return
    if member == None:
        await ctx.send("Please enter the person you want to send money to.")
        return
    bal = await update_bank(ctx.author)
    currency = bal[2]
    bal2 = await update_bank(member)
    currency2 = bal2[2]
    amount = float(amount)
    if amount > bal[1]:
        await ctx.send("You don't have enough money in your bank.")
        return
    if amount < 0:
        await ctx.send("You can't send negative money.")
        return
    if (currency != currency2):
        change = await convertCurrency(ctx.author,amount, currency, currency2)
    await update_bank(ctx.author, -1 *amount, "bank")
    await update_bank(member, change, "bank")
    await ctx.send(f"You sent {amount} {currency} to {member}.")

@client.command()
async def slots(ctx, amount = None):
    await open_account(ctx.author)
    if amount == None:
        await ctx.send("Please enter the amount you want to bet.")
        return
    bal = await update_bank(ctx.author)
    currency = bal[2]
    amount = int(amount)
    if amount > bal[0]:
        await ctx.send("You don't have enough money in your wallet.")
        return
    if amount < 0:
        await ctx.send("You can't bet negative money.")
        return
    final = []
    for i in range(3):
        a = random.choice(["X", "O", "Q"])
        final.append(a)
    await ctx.send(str(final))
    if final[0] == final[1] or final[0] == final[2] or final[1] == final[2]:
        await ctx.send(f"You won {amount} {currency}!")
        await update_bank(ctx.author, 2 * amount)
    else:
        await ctx.send(f"You lost {amount} {currency}.")
        await update_bank(ctx.author, -1 * amount)


@client.command()
async def changecur(ctx, currency = None):
    await open_account(ctx.author)
    if currency == None:
        await ctx.send("Please enter the currency you want to change to.")
        return
    users = await get_bank_data()
    if currency not in c.currencies:
        await ctx.send("That currency is not supported.")
        return
    bal = await update_bank(ctx.author)
    amount = bal[0] + bal[1]
    if amount < 0.01:
        await ctx.send("You don't have enough money to change your currency.")
        return
    bank_amt = int(bal[1] * 0.01)
    wallet_amt = int(bal[0] * 0.01)
    cur = bal[2]
    await update_bank(ctx.author, -1 * bank_amt, "bank")
    bal2 = await update_bank(ctx.author, -1 * wallet_amt, "wallet")
    users[str(ctx.author.id)]["currency"] = currency
    users[str(ctx.author.id)]["wallet"] = float(format(c.convert(bal2[0], cur, currency), ".2f"))
    users[str(ctx.author.id)]["bank"] = float(format(c.convert(bal2[1], cur, currency), ".2f"))


    with open('bank.json', 'w') as f:
        json.dump(users, f)
    
    await ctx.send(f"The exchange fee was 10% of your current money (wallet + bank). You set your currency to {currency}.")


@client.command()
async def curconvert(ctx, currency1 = None, currency2 = None):
    if currency1 == None or currency2 == None:
        await ctx.send("Please enter the currencies you want to convert.")
        return
    if currency1 not in c.currencies or currency2 not in c.currencies:
        await ctx.send("One of the currencies you entered is not supported.")
        return
    amt = format(c.convert(1, currency1, currency2), ".2f")
    await ctx.send(f"1 {currency1} = {amt} {currency2}")


async def open_account(user):
    users = await get_bank_data()
    if str(user.id) in users:
        users[str(user.id)]["wallet"] = float(users[str(user.id)]["wallet"])
        users[str(user.id)]["bank"] = float(users[str(user.id)]["bank"])
        return False
    else:
        users[str(user.id)] = {}
        users[str(user.id)]["wallet"] = 0
        users[str(user.id)]["bank"] = 0
        users[str(user.id)]["currency"] = "USD"
    with open('bank.json', 'w') as f:
        json.dump(users, f)
    return True

async def get_bank_data():
    with open('bank.json', 'r') as f:
        users = json.load(f)
    return users

async def update_bank(user, change = 0, mode = "wallet"):
    users = await get_bank_data()
    users[str(user.id)][mode] += float(format(change, '.2f'))
    with open('bank.json', 'w') as f:
        json.dump(users, f)
    bal = users[str(user.id)]["wallet"], users[str(user.id)]["bank"], users[str(user.id)]["currency"]
    return bal

async def convertCurrency(user, amount, currency1, currency2):
    users = await get_bank_data()
    users[str(user.id)]["bank"] *= 0.99
    return float(c.convert(amount, currency1, currency2))



client.run("MTEwOTQ3NDQyMTcxNjAyOTYwMA.G7AlV_.Z1jMT8lV5qCoOEFOCQrRXHUNno3serBfDJOxXE")