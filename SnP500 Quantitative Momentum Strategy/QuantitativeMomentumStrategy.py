#Momentum investing means investing in the stocks that have incrased in price the most.
#For this project, we select 50 stocks with highest price momentum, then calculate recommended trades
#for an equal-weight portfolio of these 50 stocks.

import pandas as pd
import numpy as np
import requests
import math
import xlsxwriter
#Scipy is open-source software for mathematics, science and engineering.
#We will use stats to calculate percentile scores from stock momentum metrics.
from scipy.stats import percentileofscore as score 
from statistics import mean

stocks = pd.read_csv('sp_500_stocks.csv')
from secrets import IEX_CLOUD_API_TOKEN

symbol = 'AAPL'
get_endpoint_url = f'/stock/{symbol}/stats/'
sandbox_base_url = 'https://sandbox.iexapis.com/stable'
token_handle = f'?token={IEX_CLOUD_API_TOKEN}'
api_url = f'{sandbox_base_url}{get_endpoint_url}{token_handle}'
data = requests.get(api_url).json()
print(data)
print(data['year1ChangePercent'])



def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n): #syntax for range is range(first value in range, last value in range, step size).
        yield lst[i:i + n] #yield a string array for each 100 strings in stocks.

#Call chunks function to our case.  Note that function lists can take iterator objects, such as our function chunks.
#symbol_groups is a list of lists.
symbol_groups = list(chunks(stocks['Ticker'], 100))

#create symbol_strings out of symbol_groups, where elements in each symbol string are separated by ','.
#Note this is still a list of lists.  We are just arranging the symbols/data in the format accepted by the IEX url, i.e. comma-separated.
symbol_strings = []
for i in range(0, len(symbol_groups)):
    symbol_strings.append(','.join(symbol_groups[i]))
    #print(symbol_strings[i])
print(symbol_strings)

my_columns = ['Ticker', 'Price', 'One-Year Price Return', 'Number of Shares to Buy']
final_dataframe = pd.DataFrame(columns = my_columns)
print(final_dataframe)

for symbol_string in symbol_strings:
    #using price and stats endpoints to get the data we need.
    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=price,stats&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_string.split(','):
        final_dataframe = final_dataframe.append(
            pd.Series(
                [
                    symbol,
                    data[symbol]['price'],
                    data[symbol]['stats']['year1ChangePercent'],
                    'N/A'
                    ], 
                index = my_columns),
            ignore_index = True
            )

print (final_dataframe)

#Use sort_values method to sort our data
#Arguments are (column to sort by, ascending or descending, save modifications to existing dataframe or no)
final_dataframe.sort_values('One-Year Price Return', ascending = False, inplace = True)
#Keep only first 50 entries/indices in dataframe
final_dataframe = final_dataframe[:50]
#Reset index numbering.  Drop argument drops the pre-existing jumbled index column, inplace argument keeps the new one, i.e. does final_dataframe = final_dataframe.reset_index
final_dataframe.reset_index(drop = True, inplace=True)
print(final_dataframe)

def portfolio_input():
    #Make variable global so we can use it outside the function
    global portfolio_size
    portfolio_size = input('Enter the size of your portfolio: ')
    
    try:
        float(portfolio_size)
        portfolio_size = float(portfolio_size)
    except ValueError:
        print('That is not a number! /nPlease try again.')
        portfolio_size = input('Enter the size of your portfolio: ')
        portfolio_size = float(portfolio_size)

portfolio_input()
print(portfolio_size)

position_size = portfolio_size/len(final_dataframe.index)
print(position_size)

for i in range(0, len(final_dataframe.index)):
    final_dataframe.loc[i, 'Number of Shares to Buy'] = math.floor(position_size/final_dataframe.loc[i, 'Price'])
print(final_dataframe)

#BUILDING A BETTER AND MORE REALISTIC MOMENTUM STRATEGY
#Investment strategies usually differentiate between high quality momentum stock
#and low quality momentum stock.  High-quality meaning a stock that over a long period of time shows a slow and steady stock return.
#Low quality showing surge in price over short period of time.

#Low quality momentum can be caused by short-term news that is unlikely to be repeated in the future,
#like FDA drug approval for biotech company.

#To identify high quality momentum (hqm) stocks we build a strategy that selects stocks from the highest percentiles of a basket of time-frames.

hqm_columns = [
               'Ticker', 
               'Price', 
               'Number of Shares to Buy', 
               'One-Year Price Return',
               'One-Year Return Percentile',
               'Six-Month Price Return',
               'Six-Month Return Percentile',
               'Three-Month Price Return',
               'Three-Month Return Percentile',
               'One-Month Price Return',
               'One-Month Return Percentile',
               'HQM Score'
               ]

hqm_dataframe = pd.DataFrame(columns = hqm_columns)
print(hqm_columns)

for symbol_string in symbol_strings:
    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=price,stats&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_string.split(','):
        hqm_dataframe = hqm_dataframe.append(
            pd.Series(
                [
                    symbol, 
                    data[symbol]['price'], 
                    'N/A', 
                    data[symbol]['stats']['year1ChangePercent'],
                    'N/A',
                    data[symbol]['stats']['month6ChangePercent'],
                    'N/A',
                    data[symbol]['stats']['month3ChangePercent'],
                    'N/A',
                    data[symbol]['stats']['month1ChangePercent'],
                    'N/A',
                    'N/A'
                ],
                index = hqm_columns),
            ignore_index = True
            )
    
print(hqm_dataframe)

time_periods = [
    'One-Year',
    'Six-Month',
    'Three-Month',
    'One-Month'
    ]  

for row in hqm_dataframe.index:
    for time_period in time_periods:
        price_col = f'{time_period} Price Return'
        percentile_col = f'{time_period} Return Percentile'
        #stats.percentileofscore(column from which to calculate percentile scores, data entry in the column whose perc. score we want to calculate)
        hqm_dataframe.loc[row, percentile_col] = score(hqm_dataframe[price_col], hqm_dataframe.loc[row, price_col])/100
        
print(hqm_dataframe)        
        
#HQ vs LQ stock nomenclature is due to wanting to see stock returns as a result of slow and steady business progress
#as opposed to one time big returns due to a news article.    

for row in hqm_dataframe.index:
    #Create empty list of Return Percentiles for each stock/row
    momentum_percentiles = []
    #Append/populate the list by looping over the necessary columns in our df.
    for time_period in time_periods:
        #Note .append here is Python and not Pandas function.  We are appending a list, not a df.
        momentum_percentiles.append(hqm_dataframe.loc[row, f'{time_period} Return Percentile'])
        
    #Use mean of our Return Percentiles list to create a 'HQM Score' for each stock
    hqm_dataframe.loc[row, 'HQM Score'] = mean(momentum_percentiles)

print(hqm_dataframe)
print(hqm_dataframe['HQM Score'])

#Selecting the 50 Best Momentum Stocks
#Sort dataframe based on HQM Score
hqm_dataframe.sort_values('HQM Score', ascending=False, inplace = True)
#Keep top 50 HQM scores
hqm_dataframe = hqm_dataframe[:50]
#drop = True "drops" the previous index column
hqm_dataframe.reset_index(drop = True, inplace = True)

portfolio_input()

#Note: pd.df.index returns the index column
position_size = portfolio_size/len(hqm_dataframe.index)
print(position_size)

for i in hqm_dataframe.index:
    hqm_dataframe.loc[i, 'Number of Shares to Buy'] = math.floor(position_size/hqm_dataframe.loc[i, 'Price'])


#SAVE OUR DATAFRAME TO EXCEL
#Initialize a writer object
writer = pd.ExcelWriter('momentum strategy.xlsx', engine = 'xlsxwriter')
hqm_dataframe.to_excel(writer, sheet_name = 'Momentum Strategy', index = False)

#Create Formats

background_color = '#0a0a23'
font_color = '#ffffff'

#add_format method takes dictionary as input, defined using curly {} brackets.
string_format = writer.book.add_format(
    {
        'font_color' : font_color,
        'bg_color' : background_color,
        'border' : 1 #1 means to add a solid border around each one.
        }
    )

dollar_format = writer.book.add_format(
    {
        'num_format' : '$0.00',
        'font_color' : font_color,
        'bg_color' : background_color,
        'border' : 1 #1 means to add a solid border around each one.
        }
    )

integer_format = writer.book.add_format(
    {
        'num_format' : '0',
        'font_color' : font_color,
        'bg_color' : background_color,
        'border' : 1 #1 means to add a solid border around each one.
        }
    )

percent_format = writer.book.add_format(
    {
        'num_format' : '0.0%',
        'font_color' : font_color,
        'bg_color' : background_color,
        'border' : 1 #1 means to add a solid border around each one.
        }
    )

column_formats = {
       'A' : ['Ticker', string_format], 
       'B' : ['Price', dollar_format], 
       'C' : ['Number of Shares to Buy', integer_format], 
       'D' : ['One-Year Price Return', percent_format],
       'E' : ['One-Year Return Percentile', percent_format],
       'F' : ['Six-Month Price Return', percent_format],
       'G' : ['Six-Month Return Percentile', percent_format],
       'H' : ['Three-Month Price Return', percent_format],
       'I' : [ 'Three-Month Return Percentile', percent_format],
       'J' : ['One-Month Price Return', percent_format],
       'K' : ['One-Month Return Percentile', percent_format],
       'L' : ['HQM Score', percent_format ]             
    }

for column in column_formats.keys():
    #sheets attribute in writer object is a list of all sheets in our excel file
    #set_column method sets format for a column.
    writer.sheets['Momentum Strategy'].set_column(f'{column}:{column}', 25, column_formats[column][1])
    #Format column headers/names
    writer.sheets['Momentum Strategy'].write(f'{column}1', column_formats[column][0], column_formats[column][1])

#Save our writer object/excel file
writer.save()