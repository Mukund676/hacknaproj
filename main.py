import random
import discord
from discord.ext import commands
import json
from currency_converter import CurrencyConverter
import yfinance as yf

from pandas import read_csv
c = CurrencyConverter(fallback_on_missing_rate=True)

client = commands.Bot(command_prefix = 'e!', intents=discord.Intents.all())

with(open('config.json')) as g:
    config = json.load(g)
    token = config['token']

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
    investment = users[str(ctx.author.id)]["investment"]
    embed = discord.Embed(title = f"{ctx.author.name}'s balance", color = discord.Color.red())
    embed.add_field(name = "Wallet", value = wallet_amt)
    embed.add_field(name = "Bank", value = bank_amt)
    embed.add_field(name = "Currency", value = currency)
    #find the increase or decrease in value of investment
    value = await findValOfPortfolio(ctx.author.id)
    #find net change in value of investment
    embed.add_field(name = "Investment Change", value = format((value - investment)/100, '.2f') + "%")
    await ctx.send(embed = embed)


@client.command()
async def help(ctx):
    embed = discord.Embed(title = "Help", description = "Use e! before every command. Every exchange involving multiple currencies has a fee. Ticker means stock symbol", color = discord.Color.red())
    embed.add_field(name = "balance", value = "Shows your balance.")
    embed.add_field(name = "withdraw [amount]", value = "Withdraw money from your bank.")
    embed.add_field(name = "deposit [amount]", value = "Deposit money into your bank.")
    embed.add_field(name = "transfer [@user] [amount]", value = "Send money from your bank to user's bank")
    embed.add_field(name = "send [@user] [amount]", value = "Send money from your wallet to user's wallet")
    embed.add_field(name = "rob [@user]", value = "Rob from someone, small chance of failing.")
    embed.add_field(name = "showstock [ticker]", value = "Shows information about a [ticker].")
    embed.add_field(name = "buy [ticker] [number]", value="Buy [number] of shares of a [ticker].")
    embed.add_field(name = "sell [ticker] [number]", value="Sell [number] of shares of a [ticker].")
    embed.add_field(name = "work", value="Work for money; the more you have, the more you earn")
    embed.add_field(name = "portfolio", value="Shows your portfolio.")
    embed.add_field(name = "leaderboard", value="Shows the leaderboard in your currency.")
    embed.add_field(name = "slots [amount]", value = "Play slots to bet amount of money.")
    embed.add_field(name = "validcurrs", value = "Shows all supported currencies' ISO Labels.")
    embed.add_field(name = "changecurr [currency]", value = "Convert your money to another currency. [currency ISO] is the ISO label for the currency If the currency is not supported for the date, a linear interpolation graph is used to estimate the exchange rate.")
    embed.add_field(name = "currconvert [currency1] [currency2]", value = "Get the most recent currency exchange rates.")
    await ctx.message.author.send(embed = embed)





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
async def transfer(ctx, member: discord.Member, amount = None):
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
    await ctx.send(f"You transferred {amount} {currency} to {member}'s bank.")

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
    if amount > bal[0]:
        await ctx.send("You don't have enough money in your wallet.")
        return
    if amount < 0:
        await ctx.send("You can't send negative money.")
        return
    if (currency != currency2):
        change = await convertCurrency(ctx.author,amount, currency, currency2)
    await update_bank(ctx.author, -1 *amount, "wallet")
    await update_bank(member, change, "wallet")
    await ctx.send(f"You sent {amount} {currency} to {member}.")

@client.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def work(ctx):
    await open_account(ctx.author)
    users = await get_bank_data()
    currency = users[str(ctx.author.id)]["currency"]
    earnings = random.randrange(150)
    if (users[str(ctx.author.id)]["wallet"] > 1000):
        earnings *= 3
    elif (users[str(ctx.author.id)]["wallet"] > 500):
        earnings *= 2
    
    earninginamt = c.convert(earnings, 'USD', currency)
    await ctx.send(f"You worked and earned {earnings} {currency}!!")
    users[str(ctx.author.id)]["wallet"] += earnings
    with open('bank.json', 'w') as f:
        json.dump(users, f)



@client.command()
@commands.cooldown(1, 1800, commands.BucketType.user)
async def rob(ctx, member: discord.Member):
    users = await open_account(ctx.author)
    users2 = await open_account(member)
    failchance = random.randrange(0, 100)
    bal = await update_bank(ctx.author)
    currency = bal[2]
    bal2 = await update_bank(member)
    currency2 = bal2[2]
    if failchance < 70:
        await ctx.send(f"You tried to rob {member} but you failed and got caught.")
        users[str(ctx.author.id)]["wallet"] *= 0.8
        return
    stolen = random.randrange(0, int(bal2[0]))
    if bal2[0] == 0:
        await ctx.send("They have no money in their wallet.")
        return
    change = await convertCurrency(ctx.author,stolen, currency2, currency)
    change = round(change, 2)
    await update_bank(ctx.author, change)
    await update_bank(member, -1 * stolen)
    await ctx.send(f"You robbed {member} and got {change} {currency}.")



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
    if final[0] == final[1] and final[0] == final[2]:
        await ctx.send(f"You won {amount} {currency}!")
        await update_bank(ctx.author, 2 * amount)
    else:
        await ctx.send(f"You lost {amount} {currency}.")
        await update_bank(ctx.author, -1 * amount)


@client.command()
async def changecurr(ctx, currency = None):
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
    
    await ctx.send(f"The exchange fee was 1% of your current money (wallet + bank). You set your currency to {currency}.")

@client.command()
async def showcurr(ctx):
    #show a table of all the currencies
    await ctx.send(c.currencies)


@client.command()
async def currconvert(ctx, currency1 = None, currency2 = None):
    if currency1 == None or currency2 == None:
        await ctx.send("Please enter the currencies you want to convert.")
        return
    if currency1 not in c.currencies or currency2 not in c.currencies:
        await ctx.send("One of the currencies you entered is not supported.")
        return
    amt = format(c.convert(1, currency1, currency2), ".2f")
    await ctx.send(f"1 {currency1} = {amt} {currency2}")


@client.command()
async def showstock(ctx, ticker):
    ticker = ticker.upper()
    await open_account(ctx.author)
    users = await get_bank_data()
    currency = users[str(ctx.author.id)]["currency"]
    list_of_stocks = read_csv("stocks.csv")
    if (ticker.upper() not in list_of_stocks["Symbol"].values):
        await ctx.send("That stock is not supported.")
        return
    
    stock = yf.Ticker(ticker)
    price = stock.history()['Close'].iloc[-1]
    price = c.convert(price, "USD", currency)
    price = float(format(price, ".2f"))
    embed = discord.Embed(title = "Stock " + ticker, description = stock.info["longName"] + " website: " + stock.info["website"], color = discord.Color.red())
    embed.add_field(name = "Price", value = str(price) + " " + currency, inline = False)
    embed.add_field(name = "Max Purchase Ability", value = str(int(users[str(ctx.author.id)]["wallet"] / price)) + " shares", inline = False)
    embed.add_field(name = "Industry and Sector", value = stock.info["industryDisp"] + ", " + stock.info["sector"], inline = False)
    await ctx.send(embed = embed)

@client.command()
async def leaderboard(ctx):
    #sort it with the same currency
    users = await get_bank_data()
    currency = users[str(ctx.author.id)]["currency"]
    leaderboard = []
    for user in users:
        value = await findValOfPortfolio(user)
        if users[user]["currency"] == currency:
            leaderboard.append([user, round(users[user]["wallet"] + users[user]["bank"] + value,2)])
        else:
            leaderboard.append([user, float(format(c.convert(users[user]["wallet"] + users[user]["bank"] + await findValOfPortfolio(user), users[user]["currency"], currency), ".2f"))])
    #sort it by the sum of wallet, bank, and value of portfolio
    leaderboard.sort(key = lambda x: x[1], reverse = True)
    #print the top users
    embed = discord.Embed(title = "Leaderboard", description = "Top users in leaderboard", color = discord.Color.red())
    for i in range(len(leaderboard)):
        user = client.get_user(int(leaderboard[i][0]))
        embed.add_field(name = f"{i + 1}. {user.name}", value = str(leaderboard[i][1]) + " " + currency, inline = False)
    await ctx.send(embed = embed)


@client.command()
async def buy(ctx, ticker, numShares=None):
    ticker = ticker.upper()
    await open_account(ctx.author)
    if numShares == None:
        await ctx.send("Please enter the number of shares you want to buy.")
        return
    users = await get_bank_data()
    currency = users[str(ctx.author.id)]["currency"]
    list_of_stocks = read_csv("stocks.csv")
    if (ticker.upper() not in list_of_stocks["Symbol"].values):
        await ctx.send("That stock is not supported.")
        return
    stock = yf.Ticker(ticker)
    price = stock.history()['Close'].iloc[-1]
    price = c.convert(price, "USD", currency)
    price = float(format(price, ".2f"))
    numShares = int(numShares)
    if (numShares < 0):
        await ctx.send("You can't buy negative shares.")
        return
    if (numShares * price > users[str(ctx.author.id)]["wallet"]):
        await ctx.send("You don't have enough money in your wallet to buy that many shares.")
        return
    users[str(ctx.author.id)]["wallet"] -= numShares * price
    if ticker in users[str(ctx.author.id)]["portfolio"]:
        users[str(ctx.author.id)]["portfolio"][ticker]["shares"] += numShares
        users[str(ctx.author.id)]["portfolio"][ticker]["totalvalue"] += numShares * price
    else:
        users[str(ctx.author.id)]["portfolio"][ticker] = {}
        users[str(ctx.author.id)]["portfolio"][ticker]["shares"] = numShares
        users[str(ctx.author.id)]["portfolio"][ticker]["totalvalue"] = numShares * price
    users[str(ctx.author.id)]["investment"] += numShares * price
    with open('bank.json', 'w') as f:
        json.dump(users, f)
    await ctx.send(f"You bought {numShares} shares of {ticker} for {numShares * price} {currency}.")

@client.command()
async def sell(ctx, ticker, numShares = None):
    ticker = ticker.upper()
    await open_account(ctx.author)
    users = await get_bank_data()
    if ticker not in users[str(ctx.author.id)]["portfolio"]:
        await ctx.send("You don't have any shares of that stock.")
        return
    if numShares == None:
        numShares = 1
    currency = users[str(ctx.author.id)]["currency"]
    list_of_stocks = read_csv("stocks.csv")
    if (ticker.upper() not in list_of_stocks["Symbol"].values):
        await ctx.send("That stock is not supported.")
        return
    stock = yf.Ticker(ticker)
    price = stock.history()['Close'].iloc[-1]
    price = c.convert(price, "USD", currency)
    price = float(format(price, ".2f"))
    numShares = int(numShares)
    if (numShares < 0):
        await ctx.send("You can't sell negative shares.")
        return
    if ticker not in users[str(ctx.author.id)]["portfolio"]:
        await ctx.send("You don't have any shares of that stock.")
        return
    if (numShares > users[str(ctx.author.id)]["portfolio"][ticker]["shares"]):
        await ctx.send("You don't have enough shares to sell that many.")
        return
    users[str(ctx.author.id)]["wallet"] += numShares * price
    users[str(ctx.author.id)]["portfolio"][ticker]["shares"] -= numShares
    users[str(ctx.author.id)]["portfolio"][ticker]["totalvalue"] -= numShares * price
    if users[str(ctx.author.id)]["portfolio"][ticker]["shares"] == 0:
        del users[str(ctx.author.id)]["portfolio"][ticker]
    users[str(ctx.author.id)]["investment"] -= numShares * price
    with open('bank.json', 'w') as f:
        json.dump(users, f)
    await ctx.send(f"You sold {numShares} shares of {ticker} for {numShares * price} {currency}.")


@client.command()
async def portfolio(ctx):
    await open_account(ctx.author)
    users = await get_bank_data()
    currency = users[str(ctx.author.id)]["currency"]
    if not users[str(ctx.author.id)]["portfolio"]:
        await ctx.send("You don't have any stocks in your portfolio.")
        return
    embed = discord.Embed(title = "Portfolio", color = discord.Color.red())
    for ticker in users[str(ctx.author.id)]["portfolio"]:
        stock = yf.Ticker(ticker)
        price = stock.history()['Close'].iloc[-1]
        price = c.convert(price, "USD", currency)
        price = float(format(price, ".2f"))
        embed.add_field(name = ticker, value = "Shares: " + str(users[str(ctx.author.id)]["portfolio"][ticker]["shares"]) + "\nTotal Value: " + str(users[str(ctx.author.id)]["portfolio"][ticker]["totalvalue"]) + " " + currency + "\nCurrent Price: " + str(price) + " " + currency, inline = False)
    await ctx.send(embed = embed)

async def open_account(user):
    users = await get_bank_data()
    if str(user.id) in users:
        users[str(user.id)]["wallet"] = float(users[str(user.id)]["wallet"])
        users[str(user.id)]["bank"] = float(users[str(user.id)]["bank"])
        users[str(user.id)]["currency"] = users[str(user.id)]["currency"]
        users[str(user.id)]["investment"] = float(users[str(user.id)]["investment"])
        return False
    else:
        users[str(user.id)] = {}
        users[str(user.id)]["wallet"] = 0
        users[str(user.id)]["bank"] = 0
        users[str(user.id)]["currency"] = "USD"
        users[str(user.id)]["investment"] = 0
        users[str(user.id)]["portfolio"] = {}
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


async def findValOfPortfolio(user):
    users = await get_bank_data()
    portfolio = users[str(user)]["portfolio"]
    total = 0
    for stock in portfolio:
        #find price of stock
        stock1 = yf.Ticker(stock)
        price = stock1.history()['Close'].iloc[-1]
        price = c.convert(price, "USD", users[str(user)]["currency"])
        price = float(format(price, ".2f"))
        total += price * portfolio[stock]["shares"]
    return total


client.run(token)