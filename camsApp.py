import json
import netCDF4 as nc
import os
import itertools

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


def get_boundary_box():
    lats = []
    longs = []

    for coord in args.coords:
        lats.append(round(coord[0] - 0.05, 1))
        longs.append(round(coord[1] - 0.05, 1))

    lat_min = min(lats)
    lat_max = max(lats)
    long_min = min(longs)
    long_max = max(longs)

    return [lat_max+0.1, long_min, lat_min, long_max+0.1]


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


def save_json(nc_data: nc.Dataset):
    """
    Creates .json file with data from downloaded .nc file
    :param nc_data: dataset from netCDF file
    """
    with open(f'{JSON_FILENAME}.json', 'w') as f:
        f.writelines(prepare_json(nc_data))


def read_nc_data() -> nc.Dataset:
    """
    Reads data from .netCDF file downloaded from Copernicus
    :return:
    """
    return nc.Dataset(f'{os.getcwd()}/{NC_FILENAME}.nc')


def prepare_json(nc_data: nc.Dataset) -> json.encoder:
    polls = get_polls_from_data(nc_data)
    result = {}
    poll_objects = []
    data_row = {}

    t = nc_data.variables["time"][:]
    lats = nc_data.variables["latitude"][:]
    longs = nc_data.variables["longitude"][:]

    for pol in polls:
        arr = nc_data.variables[pol][:]
        time, lvl, lat, long = arr.shape

        for i, j, k in itertools.product(range(time), range(lat), range(long)):
            value = arr[i, 0, j, k]
            data_row.update({f'{t[i]}': str(value)})
            temp_obj = {
                "lat": str(lats[j]),
                "long": str(longs[k]),
                "data": data_row
            }
            if temp_obj not in poll_objects:
                poll_objects.append(temp_obj)

        result[pol] = poll_objects

    return json.dumps(result)


def get_polls_from_data(nc_data: nc.Dataset) -> list:
    """
    :param nc_data: dataset from netCDF file
    :return: List of pollutants found in .netCDF dataset file
    """
    return [poll for poll in nc_data.variables.keys() if poll not in ['longitude', 'latitude', 'level', 'time']]


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
    arg_parser.add_argument('coords', type=lambda a: tuple(map(float, a.split(','))), nargs='+')
    arg_parser.add_argument('-i', '--interval', help='Time interval in hours. Start at 00:00', type=int, default=4,
                            metavar='')
    args = arg_parser.parse_args()

    # TEST COORDS
    # py camsApp.py a 2023-09-01 2023-09-02 50.0692 19.9667 49.997800,19.895500 50.066400,20.017300 50.026694,19.896000 50.083900,19.898800

    print('Downloading data \n')
    download_data_file()
    print(f'\nData downloaded and saved to: {NC_FILENAME}.nc  \n')
    print(f'Reading {NC_FILENAME}.nc file \n')
    data = read_nc_data()
    print(f'Results saving to: {JSON_FILENAME}.json file \n')
    save_json(data)
