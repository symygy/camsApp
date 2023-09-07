import json
import netCDF4 as nc
import os
from decimal import Decimal, ROUND_UP, ROUND_DOWN

import cdsapi
from argparse import ArgumentParser

# Lokalizacja pliku z danymi do logowania w serwisie CAMS -> %USERPROFILE%\.cdsapirc
# Na ten moment pobieram odczyty z punktu położonego najbliżej zadanych koordynatów - w przyszłości można dodać możliwość rozszerzenia obszaru, co będzie się wiązało z koniecznością obróbki większej liczby danych do formatu json
# PM2.5, PM10

NC_FILENAME = 'ens'
JSON_FILENAME = 'data'

POLLUTANTS = [
    'particulate_matter_10um',
    'particulate_matter_2.5um'
]

TYPE = {
    'a': ['analysis'],
    'f': ['forecast'],
    # 'b': ['analysis', 'forecast'] TODO
}


def calc_interval() -> list:
    """
    Returns list of time intervals in format: 02:00
    """
    return [(f'0{t}:00' if len(str(t)) == 1 else f'{t}:00') for t in range(0, 24, args.interval)]


def get_boundary_box() -> map:
    """
    :return: map object with boundary box created according to provided latitude and longitude value
    """

    args.lat = round(args.lat - 0.05, 1)
    args.long = round(args.long - 0.05, 1)
    n = args.lat + 0.1
    s = args.lat
    w = args.long
    e = args.long + 0.1

    return map(lambda x: round(x, 2), [n, w, s, e])


def download_data_file():
    """
    Connects to Copernicus database using API to retrieve data
    """
    c = cdsapi.Client()
    c.retrieve(
        'cams-europe-air-quality-forecasts',
        {
            'variable': POLLUTANTS,
            'model': 'ensemble',
            'level': '0',
            'date': f'{args.start_date}/{args.end_date}',
            'type': TYPE[args.type],
            'time': calc_interval(),
            'leadtime_hour': '0',
            'area': list(get_boundary_box()),
            'format': 'netcdf',
        },
        f'{NC_FILENAME}.nc')


def save_json(temp_data: nc.Dataset):
    """
    Creates .json file with data from downloaded .nc file
    :param temp_data: dataset from netCDF file
    """
    with open(f'{JSON_FILENAME}.json', 'w') as f:
        f.writelines(prepare_json(temp_data))


def read_nc_data() -> nc.Dataset:
    """
    Reads data from .netCDF file downloaded from Copernicus
    :return:
    """
    return nc.Dataset(f'{os.getcwd()}/{NC_FILENAME}.nc')


def prepare_json(temp_data: nc.Dataset) -> json.encoder:
    """
    Creates a json formatted data
    :param temp_data: dataset from netCDF file
    :return: data in json format
    """
    polls = get_polls_from_data(temp_data)
    result = {}
    temp_result = {}

    for pol in polls:
        for i, t in enumerate(temp_data.variables['time']):
            temp_result.update({f'{t}': round(temp_data.variables[pol][i].__float__(), 3)})
        result[pol] = {'unit': temp_data.variables[pol].units, 'readings': temp_result}

    return json.dumps(result)


def get_polls_from_data(temp_data: nc.Dataset) -> list:
    """
    :param temp_data: dataset from netCDF file
    :return: List of pollutants found in .netCDF dataset file
    """
    return [poll for poll in temp_data.variables.keys() if poll not in ['longitude', 'latitude', 'level', 'time']]


# def get_lats_and_longs_from_data(temp_data) -> dict:
#     # NOT USED
#     return {
#         "lat": list(map(lambda x: str(x), temp_data.variables['latitude'][:])),
#         "long": list(map(lambda x: str(x), temp_data.variables['longitude'][:]))
#     }

# def get_filename():
#     # NOT USED
#     if include_date_in_filename:
#         return f'{OUTPUT_FILENAME}_{datetime.datetime.now().strftime("%d%m%Y")}'
#
#     return OUTPUT_FILENAME


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('type', choices=['a', 'f'],
                            help='Type: "a" for analysis, "f" for forecast')
    arg_parser.add_argument('start_date', help='Start date [yyyy-mm-dd]', metavar='startDate')
    arg_parser.add_argument('end_date', help='End date [yyyy-mm-dd]', metavar='endDate')
    arg_parser.add_argument('lat', help='Latitude [0 - 90]', type=float)
    arg_parser.add_argument('long', help='Longitude [0 - 180]', type=float)
    arg_parser.add_argument('-i', '--interval', help='Time interval in hours. Start at 00:00', type=int, default=4,
                            metavar='')
    args = arg_parser.parse_args()
    print('Downloading data \n')
    download_data_file()
    print(f'\nData downloaded and saved to: {NC_FILENAME}.nc  \n')
    print(f'Reading {NC_FILENAME}.nc file \n')
    data = read_nc_data()
    print(f'Results saving to: {JSON_FILENAME}.json file \n')
    save_json(data)
