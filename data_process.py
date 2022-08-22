import pandas as pd
import utm
import matplotlib.pyplot as plt
import branca

from matplotlib.backends.backend_pdf import FigureCanvasPdf, PdfPages

from dateutil import parser
import folium
import math

import magic
from os import path
import datetime
from itertools import chain

from mydebug import *

import xlsxwriter

import branca.colormap as cmp

PLOTS_PER_ROW = 2
ROWS_PER_PAGE = 3

DT_LOG_TIMESTAMP = 'TIME_STAMP'
DT_LOG_LAT = 'LAT'
DT_LOG_LON = 'LON'

def load_data(filename, filetype):
    print("Loading file - " + filename)
    if not path.exists(filename):
        print("File doesn't exist - " + filename)
        exit(1)

    # load trace file to pandas dataframe according to file type
    if filetype == 'XCAP':
        dbg_print(magic.from_file(filename))
        if magic.from_file(filename) == 'Microsoft Excel 2007+':

            # read xcap file into pandas dataframe. Temporary solution: use the 2nd row as index
            xcap_file = pd.read_excel(filename, header=1)
            # print(xcap_file.columns)

            # Check Whether the XCAP export file include timestamp, geo data
            if {DT_LOG_TIMESTAMP, DT_LOG_LON, DT_LOG_LAT}.issubset(xcap_file.columns):
                # following code remove the statistics data in the last a few rows of XCAP export file through checking
                # whether the data type of column 'TIME_STAMP' is datetime.
                for index, row in xcap_file.iterrows():
#                    dbg_print(type(row['TIME_STAMP']))
                    if type(row[DT_LOG_TIMESTAMP]) != datetime.datetime and type(row[DT_LOG_TIMESTAMP]) != pd._libs.tslibs.timestamps.Timestamp:
                        xcap_file.drop(axis=0, index=index, inplace=True)

                # return XCAP export as dataframe
                return xcap_file
            else:  # assert wrong XCAL file format if timestamp and geo data are not included in XCAP export file
                print("XCAL file need to include time_stamp, Lat. Lon. information")
                exit(1)
        else:
            print("XCAP trace file is not exported as correct format, please export it as Excel format - *.xlsx")
            exit(1)
    else:
        print("File type is not supported")
        exit(1)


def write_data_to_excel(filename, tabname, data, kpi_list):
    if path.exists(filename):
        result = pd.ExcelWriter(path=filename, engine="openpyxl", mode='a')
    else:
        result = pd.ExcelWriter(path=filename, engine="openpyxl", mode='w')

    kpis = list(chain.from_iterable(kpi_list))
    final_kpis = []

    if 'tracefile' in data.columns:
        kpis.insert(0, 'tracefile')

    for kpi in kpis:
        found_kpi = False

        for col in data.columns:
            if kpi in col:
                final_kpis.append(col)
                found_kpi = True
                break

        if not found_kpi:
            print("Missing KPI: ", kpi, "in data file")
            exit(1)

    print("Writing file - " + filename)

    data.to_excel(result, sheet_name=tabname, columns=final_kpis)

    result.save()


def sample_time_binning(dataframe):
    if not 'Time' in dataframe.columns:
        print("there is no Time in dataframe!")
        return 1

    dataframe_time_index = dataframe.set_index(dataframe['Time'].map(parser.parse))

    return dataframe_time_index.resample('1s').mean()


def sample_extract_period(dataframe, timestamp_column, start_time, period):
    for index, row in dataframe.iterrows():
        if type(row[timestamp_column]) != datetime.datetime:
            print('not timestamp column')
            exit(1)

    end_time = start_time + datetime.timedelta(0, period)

    # no need to set timestamp column as index. dataframe.between_time support axis as both column and index
    df_with_timestamp_index = dataframe.set_index(pd.DatetimeIndex(dataframe[timestamp_column]))

    if end_time < df_with_timestamp_index.tail(1).index:

        # !!! Need to figure out how to work for data across different date
        extracted_data = df_with_timestamp_index.between_time(start_time.time(), end_time.time())

        return extracted_data

    else:
        return None

# old implementation
#    if extracted_data.tail(1).index < end_time:
#        return None
#    else:
#        return extracted_data


def sample_discrete(dataframe, discrete_parameter, bin, method='mean', curve_datafile=None):
    if not discrete_parameter in dataframe.columns:
        print("there is no discrete parameter in the dataframe!")
        return 1

    dataframe['discrete'] = pd.cut(dataframe[discrete_parameter], bin)

    if method == 'mean':
        discrete_data = dataframe.groupby(['discrete']).mean()
    elif method == 'median':
        discrete_data = dataframe.groupby(['discrete']).median()
    else:
        print('wrong method')
        exit(1)

    if not (curve_datafile is None):
        print(discrete_data)
        discrete_data.to_excel(curve_datafile)

    return discrete_data


def sample_spatial_binning(dataframe, bin_size, binningfile=None, method='mean'):
    longitude = DT_LOG_LON
    latitude = DT_LOG_LAT

    dbg_print(' ----- binnning data to '+str(bin_size)+'m x '+str(bin_size)+'m area -----')

    if not longitude in dataframe.columns:
        print("there is no longitude in the dataframe!")
        return 1

    if not latitude in dataframe.columns:
        print("there is no latitude in the dataframe!")
        return 1
    #   def get_utm(row):
    #           print(row)
    #           tup = tuple(ti // bin_size for ti in utm.from_latlon(row.ix[0], row.ix[1])[:2])
    #           return pd.Series(tup)

    #       dataframe[['utm_x', 'utm_y']] = dataframe[[latitude, longitude]].apply(get_utm, axis=1)

    for i in range(len(dataframe)):
        dataframe.loc[i, 'utm_x'] = utm.from_latlon(dataframe.loc[i, latitude], dataframe.loc[i, longitude])[
                                        0] // bin_size
        dataframe.loc[i, 'utm_y'] = utm.from_latlon(dataframe.loc[i, latitude], dataframe.loc[i, longitude])[
                                        1] // bin_size

    if method == 'mean':
        binning_dataframe = dataframe.groupby(['utm_x', 'utm_y'], as_index=False).mean()
    elif method == 'median':
        binning_dataframe = dataframe.groupby(['utm_x', 'utm_y'], as_index=False).median()

    for i in range(len(binning_dataframe)):
        zone_number = utm.latlon_to_zone_number(binning_dataframe.loc[i, latitude], binning_dataframe.loc[i, longitude])
        zone_letter = utm.latitude_to_zone_letter(binning_dataframe.loc[i, latitude])

        binning_dataframe.loc[i, 'binned_lat'] = utm.to_latlon(float(binning_dataframe.loc[i, 'utm_x'] * bin_size)
                                                               + float(bin_size / 2),
                                                               float(binning_dataframe.loc[i, 'utm_y'] * bin_size)
                                                               + float(bin_size / 2), zone_number, zone_letter)[0]
        binning_dataframe.loc[i, 'binned_lon'] = utm.to_latlon(float(binning_dataframe.loc[i, 'utm_x'] * bin_size)
                                                               + float(bin_size / 2),
                                                               float(binning_dataframe.loc[i, 'utm_y'] * bin_size)
                                                               + float(bin_size / 2), zone_number, zone_letter)[1]

    if not (binningfile is None):
        binning_dataframe.to_excel(binningfile)

    return binning_dataframe


def sample_plot_on_map(kpi_map: folium.Map, dataframe: pd.DataFrame, kpi, geoplotting_datafile, color_set):
    longitude = 'binned_lon'
    latitude = 'binned_lat'

    dbg_print(' ----- plotting data to '+kpi+' on map -----')

    if not longitude in dataframe.columns:
        print("there is no longitude in the dataframe!")
        return 1

    if not latitude in dataframe.columns:
        print("there is no latitude in the dataframe!")
        return 1

    if not kpi in dataframe.columns:
        print("there is no kpi in dataframe!")
        return 1

    dbg_print(kpi_map)

    kpi_map.fit_bounds([[dataframe[latitude].min(), dataframe[longitude].min()],
                        [dataframe[latitude].max(), dataframe[longitude].max()]])

    folium.TileLayer('Stamen Terrain').add_to(kpi_map)
    folium.TileLayer('CartoDB positron').add_to(kpi_map)
    #folium.TileLayer('Mapbox Bright').add_to(map)
    #folium.TileLayer('Cloudmade').add_to(map)
    #folium.TileLayer('Mapbox').add_to(map)
    folium.LayerControl().add_to(kpi_map)

    step = cmp.StepColormap(
        ['yellow', 'green', 'purple'],
        vmin=-130, vmax=-40,
        index=[-130, -100, -80, -40],  # for change in the colors, not used fr linear
        caption='Color Scale for Map'  # Caption for Color scale or Legend
    )

#    dataframe.apply(lambda row: folium.RegularPolygonMarker(location=[row[latitude], row[longitude]],
#                                                            `fill=True, fill_color='YlGn', radius=2`).add_to(kpi_map),
#                    axis=1)

    kpi_map.save(geoplotting_datafile)

    # return map


def sample_plot_on_map_to_file(dataframe, kpi, geoplotting_datafile, color_set):
    longitude = 'binned_lon'
    latitude = 'binned_lat'

    dbg_print(' ----- plotting data to '+kpi+' on map -----')

    if not longitude in dataframe.columns:
        print("there is no longitude in the dataframe!")
        return 1

    if not latitude in dataframe.columns:
        print("there is no latitude in the dataframe!")
        return 1

    if not kpi in dataframe.columns:
        print("there is no kpi in dataframe!")
        return 1

    map = folium.Map(location=[dataframe[latitude].mean(), dataframe[longitude].mean()],
                     zoom_start=13)

    map.fit_bounds([[dataframe[latitude].min(), dataframe[longitude].min()],
                    [dataframe[latitude].max(), dataframe[longitude].max()]])

    folium.TileLayer('Stamen Terrain').add_to(map)
    folium.TileLayer('CartoDB positron').add_to(map)
    #folium.TileLayer('Mapbox Bright').add_to(map)
    #folium.TileLayer('Cloudmade').add_to(map)
    #folium.TileLayer('Mapbox').add_to(map)
    folium.LayerControl().add_to(map)

    step = cmp.StepColormap(
        ['yellow', 'green', 'purple'],
        vmin=-130, vmax=-40,
        index=[-130, -100, -80, -40],  # for change in the colors, not used fr linear
        caption='Color Scale for Map'  # Caption for Color scale or Legend
    )

    dataframe.apply(
        lambda row: folium.RegularPolygonMarker(location=[row[latitude], row[longitude]], fill=True, fill_color='YlGn', radius=2).add_to(
            map), axis=1)

    map.save(geoplotting_datafile)

    return map


def plot_ssv_kpi(data, x_axis, kpi_list, timeline, period):
    i = 0

    plots_per_row = PLOTS_PER_ROW
    # rows_of_plots = math.ceil(len(kpi_list) / plots_per_row)
    rows_of_plots = ROWS_PER_PAGE

    end_timeline = timeline + datetime.timedelta(0, period)

    for kpi in kpi_list:
        dbg_print("plot kpi: " + kpi)
        for col in data.columns:
            if not kpi in col:
                dbg_print(kpi + ' is not in the dataframe')
                exit(1)

        if i % (plots_per_row * rows_of_plots) == 0:
            figure, axes = plt.subplots(rows_of_plots, plots_per_row)

        dataplot = data.plot(ax=axes[int((i % (plots_per_row * rows_of_plots)) / plots_per_row), (i % plots_per_row)],
                             kind='line', x=x_axis, y=kpi, title=kpi, figsize=(12, 15))

        dataplot.axvline(timeline, color='red', linestyle='--')
        dataplot.axvline(end_timeline, color='red', linestyle='--')

        i = i + 1

    # plt.tight_layout()
    plt.show()


def plot_dt_kpi_to_pdf(filename, data, x_axis, kpi_list, timeline=None, period=None):
    i = 0

    plots_per_row = PLOTS_PER_ROW
    rows_of_plots = ROWS_PER_PAGE

    # flatten 2D KPI list to 1D KPI list
    kpis = list(chain.from_iterable(kpi_list))

    figure, axes = plt.subplots(rows_of_plots, plots_per_row)

    if not (timeline is None):
        end_timeline = timeline + datetime.timedelta(0, period)

    with PdfPages(filename) as pdf:
        for kpis in kpi_list:

            for kpi in kpis:
                dbg_print("plot kpi: " + kpi)

                # check kpi is included in dataframe
                found_kpi = False
                for col in data.columns:
                    if kpi in col:
                        found_kpi = True
                        kpi = col
                        break

                if not found_kpi:
                    print(kpi + ' is not in the dataframe')
                    dbg_print(kpi + ' is not in the dataframe')
                    exit(1)

                # if pd.api.types.is_number(data[kpi]):
                dataplot = data.plot.hist(bins=100,
                                          ax=axes[int((i % (plots_per_row * rows_of_plots)) / plots_per_row),
                                                  (i % plots_per_row)], y=kpi, title=kpi, figsize=(15, 18))

            if not (timeline is None):
                dataplot.axvline(timeline, color='red', linestyle='--')
                dataplot.axvline(end_timeline, color='red', linestyle='--')

            i = i + 1

            if i % (plots_per_row * rows_of_plots) == 0:
                pdf.savefig(figure)
                plt.close('all')
                figure, axes = plt.subplots(rows_of_plots, plots_per_row)

        pdf.savefig(figure)
        plt.close('all')


def statistics_dt_kpi_to_excel(filename, data, kpi_list):

    try:
        exportfile = xlsxwriter.Workbook(filename)
    except:
        print('File write error!')
        exit(1)

    # flatten 2D KPI list to 1D KPI list
    kpis = list(chain.from_iterable(kpi_list))

    kpis_final = []

    # check kpi is included in dataframe
    for kpi in kpis:
        found_kpi = False
        for col in data.columns:
            if kpi in col:
                found_kpi = True
                kpis_final.append(col)
                break

        if not found_kpi:
            print(kpi + ' is not in the dataframe')
            dbg_print(kpi + ' is not in the dataframe')
            exit(1)

    data[kpis_final].describe(percentiles=[0.05, 0.1, 0.5, 0.9, 0.97]).to_excel(filename)


def plot_ssv_kpi_to_pdf(filename, data, x_axis, kpi_list, timeline=None, period=None):
    i = 0

    plots_per_row = PLOTS_PER_ROW
    rows_of_plots = ROWS_PER_PAGE

    # figure, axes = plt.subplots(rows_of_plots, plots_per_row)
    figure, axes = plt.subplots(rows_of_plots, plots_per_row)
    figure.subplots_adjust(hspace=0.8)

    if not (timeline is None):
        end_timeline = timeline + datetime.timedelta(0, period)

    with PdfPages(filename) as pdf:
        for kpis in kpi_list:

            for kpi in kpis:
                found_kpi = False

                dbg_print("plot kpi: " + kpi)

                # check kpi is included in dataframe
                for col in data.columns:
                    if kpi in col:
                        kpi_in_dataframe = col
                        found_kpi = True
                        break

                if not found_kpi:
                    print(kpi + ' is not in the dataframe')
                    dbg_print(kpi + ' is not in the dataframe')
                    exit(1)

                if not pd.api.types.is_string_dtype(data[kpi_in_dataframe]):
                    dataplot = data.plot(ax=axes[int((i % (plots_per_row * rows_of_plots)) / plots_per_row),
                                                 (i % plots_per_row)], kind='line', x=x_axis, y=kpi_in_dataframe,
                                         title=kpi, figsize=(15, 15), marker='.')
                    dataplot.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), fancybox=True, shadow=True)

            if not (timeline is None):
                dataplot.axvline(timeline, color='red', linestyle='--')
                dataplot.axvline(end_timeline, color='red', linestyle='--')

            i = i + 1

            if i % (plots_per_row * rows_of_plots) == 0:
                pdf.savefig(figure)
                plt.close('all')
                figure, axes = plt.subplots(rows_of_plots, plots_per_row, figsize=(15, 15))
                figure.subplots_adjust(hspace=0.8)

        pdf.savefig(figure)
        plt.close('all')


def calculate_best_avg_ssv_kpi(data, timestamp, kpi, period):
    best_avg_ssv_dl_throughput = 0
    best_avg_ssv_dl_period = 0

    if not {timestamp, kpi}.issubset(data.columns):
        dbg_print('no required timestamp or kpi')
        return None

    for index, row in data.iterrows():
        sliding_window_kpi = sample_extract_period(data, timestamp, row[timestamp], period - 1)

        if sliding_window_kpi is None:
            dbg_print('The remaining data does not cover the whole ' + str(period) + 'seconds period')
            break

        sliding_window_avg_ssv_dl_throughput = sliding_window_kpi[kpi].mean()

        if sliding_window_avg_ssv_dl_throughput > best_avg_ssv_dl_throughput:
            best_avg_ssv_dl_period = row[timestamp]
            best_avg_ssv_dl_throughput = sliding_window_avg_ssv_dl_throughput

        dbg_print('Best kpi: ' + str(best_avg_ssv_dl_throughput) + ' sliding window kpi: ' + str(
            sliding_window_avg_ssv_dl_throughput) + 'Mbps @ ' + str(row[timestamp]))

    print("########### Sliding window reaches the end. Best kpi: ", best_avg_ssv_dl_throughput, '@',
          best_avg_ssv_dl_period, '###########')
    return sample_extract_period(data, timestamp, best_avg_ssv_dl_period, period - 1), best_avg_ssv_dl_period
