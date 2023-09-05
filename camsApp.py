import math
from decimal import Decimal, ROUND_UP, ROUND_DOWN

import cdsapi
from argparse import ArgumentParser

# Lokalizacja pliku z danymi do logowania w serwisie CAMS -> %USERPROFILE%\.cdsapirc
# PM2.5, PM10

TYPE = {
    'a': ['analysis'],
    'f': ['forecast'],
    'b': ['analysis', 'forecast']
}

correction_idx = 0.2

# 54.56174 - 0.2 = 54.36 -> 54.35
# 54.56174 + 0.2 = 54.76 -> 54.75

arg_parser = ArgumentParser()
arg_parser.add_argument('type', choices=['a', 'f', 'b'], help='Type: "a" for analysis, "f" for forecast, "b" for both')
arg_parser.add_argument('start_date', help='Start date [yyyy-mm-dd]', metavar='startDate')
arg_parser.add_argument('end_date', help='End date [yyyy-mm-dd]', metavar='endDate')
arg_parser.add_argument('lat', help='Latitude [0 - 90]', type=float)
arg_parser.add_argument('long', help='Longitude [0 - 180]', type=float)
arg_parser.add_argument('-i', '--interval', help='Time interval in hours. Start at 00:00', type=int, default=4,
                        metavar='')

args = arg_parser.parse_args()


def calc_interval():
    return [(f'0{t}:00' if len(str(t)) == 1 else f'{t}:00') for t in range(0, 24, args.interval)]


def get_rounded(num, base=0.05, rounding=ROUND_UP):
    base = Decimal(base)
    return float(base * (Decimal(num) / base).quantize(1, rounding=rounding))


def get_boundary_box():
    n = get_rounded(args.lat, rounding=ROUND_UP)
    w = get_rounded(args.long, rounding=ROUND_DOWN)
    s = get_rounded(args.lat, rounding=ROUND_DOWN)
    e = get_rounded(args.long, rounding=ROUND_UP)

    return map(lambda x: round(x, 2), [n, w, s, e])


def download_data_file():
    c = cdsapi.Client()
    c.retrieve(
        'cams-europe-air-quality-forecasts',
        {
            'variable': ['particulate_matter_10um', 'particulate_matter_2.5um'],
            'model': 'ensemble',
            'level': '0',
            'date': f'{args.start_date}/{args.end_date}',
            'type': TYPE[args.type],
            'time': calc_interval(),
            'leadtime_hour': '0',
            'area': list(get_boundary_box()),
            'format': 'netcdf',
        },
        'download.nc')


if __name__ == '__main__':
    print('Downloading data \n')
    download_data_file()
    print('\n Data downloaded \n')

# TODO
# Znaleźć punkty najbliższe packzomatowi czyli juz po otrzymaniu pliku nc, musze uzyskac 4 graniczne punkty ktore sa najblizsze, a nastepnie wyodrebnic dla nich dane
