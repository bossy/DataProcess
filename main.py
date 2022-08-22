import os
import io
import datetime

import folium
from folium.plugins import Draw
import pandas
import pandas as pd
import numpy

import sys
from PyQt5.QtCore import Qt, QStringListModel, QAbstractTableModel, QModelIndex, QUrl, QTemporaryFile
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from data_process import *
from data_structure import *

from PyQt5.QtWebEngineWidgets import QWebEngineView
from IPython.display import display

# =============== Global =================
filetype = 'XCAP'

SSV_THROUGHPUT_PERIOD = 60  # seconds

nr_sinr_bin_size = numpy.arange(-9.5, 30.5, 1)
nr_rsrp_bin_size = numpy.arange(-130.5, -40.5, 1)
nr_pl_bin_size = numpy.arange(60.5, 160.5, 1)
nr_pusch_power_bin_size = numpy.arange(-1.5, 23.5, 1)

lte_sinr_bin_size = numpy.arange(-5.5, 30.5, 1)
lte_rsrp_bin_size = numpy.arange(-124.5, -40.5, 1)

distance_bin_size = numpy.arange(0, 1000, 10)
# =============== End =================

# ================== DT Test ====================
DT_TYPE = '4G_DT'

# Drive Test Data Input for Feilding
if DT_TYPE == '4G_DT':
    SINR_BIN_SIZE = lte_sinr_bin_size
    RSRP_BIN_SIZE = lte_rsrp_bin_size
    SINR_BIN_KPI = 'LTE KPI PCell SINR [dB]'
    RSRP_BIN_KPI = 'LTE KPI PCell Serving RSRP [dBm]'
    AREA_BINNING_SIZE = 20
    STATISTICS_LIST = lte_ssv_dl_thp_export_list
    dt_trace = "C:\Work\Spark_5G\Dunedin\Field_Test\DN2\\Pre_TC9_CA_DL_PS LONG CALL_KPIs Export_DN2_RSRP Filter.xlsx"

if DT_TYPE == '5G_DT':
# Drive Test Data Input for 5G20A feature
    SINR_BIN_SIZE = nr_sinr_bin_size
    RSRP_BIN_SIZE = nr_rsrp_bin_size
    RSRP_BIN_SIZE_2 = lte_rsrp_bin_size
    PL_BIN_SIZE = nr_pl_bin_size
    DISTANCE_BIN_SIZE = distance_bin_size
    PUSCH_POWER_BIN_SIZE = nr_pusch_power_bin_size
    SINR_BIN_KPI = '5G-NR PCell RF Serving SS-SINR [dB]'
    RSRP_BIN_KPI = '5G-NR PCell RF Serving SS-RSRP [dBm]'
    RSRP_BIN_KPI_2 = 'LTE KPI PCell Serving RSRP [dBm]'
    PL_BIN_KPI = '5G-NR PCell RF Pathloss [dB]'
    NR_PUSCH_POWER_BIN_KPI = '5G-NR PCell RF PUSCH Power [dBm]'
    DISTANCE_BIN_KPI = 'PCell Summary Serving Distance'
    AREA_BINNING_SIZE = 10
    # STATISTICS_LIST = Spark_DT_ENDC_DL_Export_list_New
    # STATISTICS_LIST = Spark_DT_ENDC_DL_Export_list_New2
    STATISTICS_LIST = Spark_DT_Beamforming_DL_Export_list_2_no_BF
    dt_trace = 'C:\Work\Spark_5G\Dunidin\Acceptance\Spark_Golden_Cluster\Palmerston_North_nonBF\DL_NR\\drive9_nr_dl_thp_0ocns_pure_5g.xlsx'

# Drive Test Data Input for 5G20A feature
if DT_TYPE == '5G_DT_Scanner':
    SINR_BIN_SIZE = nr_sinr_bin_size
    RSRP_BIN_SIZE = nr_rsrp_bin_size
    RSRP_BIN_SIZE_2 = lte_rsrp_bin_size
    PL_BIN_SIZE = nr_pl_bin_size
    DISTANCE_BIN_SIZE = distance_bin_size
    PUSCH_POWER_BIN_SIZE = nr_pusch_power_bin_size
    SINR_BIN_KPI = 'Top Set Top 1 SSS_CINR [dB]'
    RSRP_BIN_KPI = 'Top Set Top 1 SSS_RP [dBm]'
    # RSRP_BIN_KPI_2 = 'LTE KPI PCell Serving RSRP [dBm]'
    # PL_BIN_KPI = '5G-NR PCell RF Pathloss [dB]'
    # NR_PUSCH_POWER_BIN_KPI = '5G-NR PCell RF PUSCH Power [dBm]'
    # DISTANCE_BIN_KPI = 'PCell Summary Serving Distance'
    AREA_BINNING_SIZE = 10
    # STATISTICS_LIST = Spark_DT_ENDC_DL_Export_list_New
    # STATISTICS_LIST = Spark_DT_ENDC_DL_Export_list_New2
    STATISTICS_LIST = Spark_DT_ENDC_Thick_Scanner
    dt_trace = 'C:\Work\Spark_5G\Dunidin\Field_Test\DN2_DN4_5G\\DN2&DN4_5G_BAU_DL Sanner beamforming_KPI.xlsx'

# ================== DT Test End ====================

'''=============================================== SSV ====================================================='''
''' trace_folder = 'C:\Work\Spark_5G\\NPI\\NewRelease_2021\\5G FDD\Model\\throughput_result' '''
trace_folder = "C:\Work\Spark_5G\Feilding\Test\SSV\Post_Swap\CFDS\Process"

site_list = ['TCEOK', 'TCEMK']
sector_list = ['S1', 'S3']
calltype_list = ['ENDC']
# site_list = ['LTE5740']
# sector_list = ['On', 'Off']
# calltype_list = ['ENDC', 'LTE']
direction_list = ['DL', 'UL']

'''=============================================== SSV End ====================================================='''


def ssv_kpi_summary(path):

    # assert kpi path is valid
    if not os.path.isdir(path):
        print('Please choose a kpi folder')
        exit(1)

    # Create folder for saving result and create final result file
    result_folder = os.path.join(path, 'SSV_Result_' + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    if not os.path.exists(result_folder):
        os.mkdir(result_folder)
    result_output_file = os.path.join(result_folder, 'SSV_Result_' +
                                      datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + '.xlsx')

    print('======= Start SSV KPI analysis =======')

    # list all trace file
    trace_file_list = os.listdir(path)

    # Seperate uplink or downlink test first
    for direction in direction_list:
        direction_matching = [i for i in trace_file_list if direction in i]
        dbg_print(direction_matching)

        # Seperate different carrier secondly
        for calltype in calltype_list:
            calltype_matching = [i for i in direction_matching if calltype in i]
            dbg_print(calltype_matching)
            if not calltype_matching:
                continue

            tab_name = str(direction) + '_' + str(calltype)

            if direction == 'ul' or direction == 'UL':
                if calltype == '5g':
                    export_kpi_list = nr_ssv_ul_thp_export_list
                    searching_kpi_list = SSV_NR_UL_THROUGHPUT_KPI
                elif calltype == 'endc' or calltype == 'ENDC':
                    export_kpi_list = endc_ssv_ul_thp_export_list
                    searching_kpi_list = SSV_ENDC_UL_THROUGHPUT_KPI
                elif calltype == 'L700' or calltype == 'L1800' or calltype == 'L2600' or calltype == 'L2300' \
                        or calltype == '4g' or calltype == '4G' or calltype == 'LTE':
                    export_kpi_list = lte_ssv_ul_thp_export_list
                    searching_kpi_list = SSV_LTE_UL_THROUGHPUT_KPI
                elif calltype == 'CA':
                    export_kpi_list = lte_ssv_ca_ul_thp_export_list
                    searching_kpi_list = SSV_CA_UL_THROUGHPUT_KPI
                else:
                    dbg_print('Wrong calltype')
                    exit(1)
            elif direction == 'dl' or direction == 'DL':
                if calltype == '5g':
                    export_kpi_list = nr_ssv_dl_thp_export_list
                    searching_kpi_list = SSV_NR_DL_THROUGHPUT_KPI
                elif calltype == 'endc' or calltype == 'ENDC':
                    # export_kpi_list = endc_ssv_dl_thp_export_list
                    export_kpi_list = endc_thick_ssv_dl_thp_export_list
                    searching_kpi_list = SSV_ENDC_DL_THROUGHPUT_KPI
                elif calltype == 'L700' or calltype == 'L1800' or calltype == 'L2600' or calltype == 'L2300' \
                        or calltype == '4g' or calltype == '4G' or calltype == 'LTE':
                    # export_kpi_list = lte_ssv_dl_thp_export_list
                    export_kpi_list = lte_thick_ssv_dl_thp_export_list
                    searching_kpi_list = SSV_LTE_DL_THROUGHPUT_KPI
                elif calltype == 'CA':
                    export_kpi_list = lte_ssv_ca_dl_thp_export_list
                    searching_kpi_list = SSV_CA_DL_THROUGHPUT_KPI
                else:
                    dbg_print('Wrong calltype')
                    exit(1)
            else:
                dbg_print('Wrong direction')
                exit(1)

            # Final SSV data to write to excel file
            data_final = pd.DataFrame()

            for site in site_list:
                site_matching = [i for i in calltype_matching if site in i]
                dbg_print(site_matching)
                if not site_matching:
                    continue

                for sector in sector_list:
                    sector_matching = [i for i in site_matching if sector in i]
                    dbg_print(sector_matching)
                    if not sector_matching:
                        continue

                    for trace_file in sector_matching:
                        print('========== Analyzing Trace: ', trace_file, '==========')

                        # SSV result chart file
                        result_output_file_charts = os.path.join(result_folder,
                                                                 trace_file.split('.')[0] + '_ssv_chart.pdf')

                        # load SSV raw data file
                        data = load_data(os.path.join(path, trace_file), filetype)

                        if 'APP All FWD Throughput (kbps)' in data.columns:
                            data['APP All FWD Throughput (kbps)'] = data['APP All FWD Throughput (kbps)'].apply(lambda x: x/1000)

                        if 'APP All FWD Throughput (kbps)' in data.columns:
                            data['APP All RVS Throughput (kbps)'] = data['APP All RVS Throughput (kbps)'].apply(lambda x: x/1000)

                        # filter KPIs which is included in the data file
                        export_kpi_list_local = []

                        for kpi_group in export_kpi_list:
                            final_kpi_list = []

                            for kpi in kpi_group:
                                drop_kpi = True

                                for col in data.columns:
                                    if kpi in col:
                                        final_kpi_list.append(kpi)
                                        # Replace the raw data KPI name with the standard KPI name
                                        data.rename(columns={col: kpi}, inplace=True)
                                        drop_kpi = False
                                        break

                                if drop_kpi:
                                    print('!!! drop kpi: ', kpi, 'for site: ', site)

                            if final_kpi_list:
                                export_kpi_list_local.append(final_kpi_list)

                        # find the best average period
                        best_ssv_avg_data, best_ssv_avg_timestamp = calculate_best_avg_ssv_kpi(data, XCAL_TIME_STAMP,
                                                                                               searching_kpi_list,
                                                                                               SSV_THROUGHPUT_PERIOD)
                        # find the max sample
                        best_ssv_max_data, best_ssv_max_timestamp = calculate_best_avg_ssv_kpi(data, XCAL_TIME_STAMP,
                                                                                               searching_kpi_list,
                                                                                               1)

                        # combine average and max sample
                        data_all = pd.concat([best_ssv_avg_data.mean().to_frame().transpose().round(decimals=12),
                                              best_ssv_max_data.round(decimals=12)])

                        data_all.insert(loc=0, column='tracefile', value=[trace_file, trace_file])

                        data_final = data_final.append(data_all)

                        plot_ssv_kpi_to_pdf(result_output_file_charts, data, XCAL_TIME_STAMP,
                                            export_kpi_list_local, best_ssv_avg_timestamp, SSV_THROUGHPUT_PERIOD)

            if not data_final.empty:
                write_data_to_excel(result_output_file, tab_name, data_final, export_kpi_list_local)

def drive_test_post_process(tracefile):
    if not os.path.exists(tracefile):
        print('Trace file does not exist')
        exit(1)

    data = load_data(tracefile, filetype)

    rsrp_curve_datafile = os.path.join(os.path.dirname(tracefile),
                                       os.path.basename(tracefile).split('.')[0] + '_rsrp_curve.xlsx')
    rsrp_curve_datafile_2 = os.path.join(os.path.dirname(tracefile),
                                         os.path.basename(tracefile).split('.')[0] + '_rsrp_curve_2.xlsx')
    sinr_curve_datafile = os.path.join(os.path.dirname(tracefile),
                                       os.path.basename(tracefile).split('.')[0] + '_sinr_curve.xlsx')
    pl_curve_datafile = os.path.join(os.path.dirname(tracefile),
                                     os.path.basename(tracefile).split('.')[0] + '_pathloss_curve.xlsx')
    nr_pusch_power_datafile = os.path.join(os.path.dirname(tracefile),
                                           os.path.basename(tracefile).split('.')[0] + '_nr_pusch_power_curve.xlsx')
    distance_datafile = os.path.join(os.path.dirname(tracefile),
                                     os.path.basename(tracefile).split('.')[0] + '_distance_curve.xlsx')
    binning_datafile = os.path.join(os.path.dirname(tracefile),
                                    os.path.basename(tracefile).split('.')[0] + '_binning.xlsx')
    statistics_datafile = os.path.join(os.path.dirname(tracefile),
                                       os.path.basename(tracefile).split('.')[0] + '_statistics.xlsx')
    plot_datafile = os.path.join(os.path.dirname(tracefile),
                                 os.path.basename(tracefile).split('.')[0] + '_plotting.pdf')
    geoplotting_datafile = os.path.join(os.path.dirname(tracefile),
                                        os.path.basename(tracefile).split('.')[0] + '_geoplotting.html')

    # filter KPIs which is included in the data file
    export_kpi_list_local = []

    for kpi_group in STATISTICS_LIST:
        final_kpi_list = []

        for kpi in kpi_group:
            drop_kpi = True

            for col in data.columns:
                if kpi in col:
                    final_kpi_list.append(kpi)
                    # Replace the raw data KPI name with the standard KPI name
                    data.rename(columns={col: kpi}, inplace=True)
                    drop_kpi = False
                    break

            if drop_kpi:
                print('!!! drop kpi: ', kpi)

        if final_kpi_list:
            export_kpi_list_local.append(final_kpi_list)

    binning_data = sample_spatial_binning(data, AREA_BINNING_SIZE, binning_datafile, 'median')

    sample_plot_on_map_to_file(binning_data, RSRP_BIN_KPI, geoplotting_datafile, '')

    plot_dt_kpi_to_pdf(plot_datafile, binning_data, XCAL_TIME_STAMP, export_kpi_list_local)

    sample_discrete(binning_data, RSRP_BIN_KPI, RSRP_BIN_SIZE, 'median', rsrp_curve_datafile)
    sample_discrete(binning_data, SINR_BIN_KPI, SINR_BIN_SIZE, 'median', sinr_curve_datafile)
    if DT_TYPE == '5G_DT':
        sample_discrete(binning_data, RSRP_BIN_KPI_2, RSRP_BIN_SIZE_2, 'median', rsrp_curve_datafile_2)
        sample_discrete(binning_data, PL_BIN_KPI, PL_BIN_SIZE, 'median', pl_curve_datafile)
        sample_discrete(binning_data, NR_PUSCH_POWER_BIN_KPI, PUSCH_POWER_BIN_SIZE, 'median', nr_pusch_power_datafile)
        # sample_discrete(binning_data, DISTANCE_BIN_KPI, DISTANCE_BIN_SIZE, 'median', distance_datafile)

    statistics_dt_kpi_to_excel(statistics_datafile, binning_data, export_kpi_list_local)


def drive_test_scanner_post_process(tracefile):
    if not os.path.exists(tracefile):
        print('Trace file does not exist')
        exit(1)

    data = load_data(tracefile, filetype)

    rsrp_curve_datafile = os.path.join(os.path.dirname(tracefile),
                                    os.path.basename(tracefile).split('.')[0] + '_rsrp_curve.xlsx')
    rsrp_curve_datafile_2 = os.path.join(os.path.dirname(tracefile),
                                    os.path.basename(tracefile).split('.')[0] + '_rsrp_curve_2.xlsx')
    sinr_curve_datafile = os.path.join(os.path.dirname(tracefile),
                                    os.path.basename(tracefile).split('.')[0] + '_sinr_curve.xlsx')
    pl_curve_datafile = os.path.join(os.path.dirname(tracefile),
                                    os.path.basename(tracefile).split('.')[0] + '_pathloss_curve.xlsx')
    nr_pusch_power_datafile = os.path.join(os.path.dirname(tracefile),
                                    os.path.basename(tracefile).split('.')[0] + '_nr_pusch_power_curve.xlsx')
    distance_datafile = os.path.join(os.path.dirname(tracefile),
                                    os.path.basename(tracefile).split('.')[0] + '_distance_curve.xlsx')
    binning_datafile = os.path.join(os.path.dirname(tracefile),
                                    os.path.basename(tracefile).split('.')[0] + '_binning.xlsx')
    statistics_datafile = os.path.join(os.path.dirname(tracefile),
                                       os.path.basename(tracefile).split('.')[0] + '_statistics.xlsx')
    plot_datafile = os.path.join(os.path.dirname(tracefile),
                                 os.path.basename(tracefile).split('.')[0] + '_plotting.pdf')
    geoplotting_datafile = os.path.join(os.path.dirname(tracefile), os.path.basename(tracefile).split('.')[0] + '_geoplotting.html')

    # filter KPIs which is included in the data file
    export_kpi_list_local = []

    for kpi_group in STATISTICS_LIST:
        final_kpi_list = []

        for kpi in kpi_group:
            drop_kpi = True

            for col in data.columns:
                if kpi in col:
                    final_kpi_list.append(kpi)
                    # Replace the raw data KPI name with the standard KPI name
                    data.rename(columns={col: kpi}, inplace=True)
                    drop_kpi = False
                    break

            if drop_kpi:
                print('!!! drop kpi: ', kpi)

        if final_kpi_list:
            export_kpi_list_local.append(final_kpi_list)

    binning_data = sample_spatial_binning(data, AREA_BINNING_SIZE, binning_datafile, 'median')

    sample_plot_on_map(binning_data, RSRP_BIN_KPI, geoplotting_datafile, '')

    plot_dt_kpi_to_pdf(plot_datafile, binning_data, XCAL_TIME_STAMP, export_kpi_list_local)

    sample_discrete(binning_data, RSRP_BIN_KPI, RSRP_BIN_SIZE, 'median', rsrp_curve_datafile)
    sample_discrete(binning_data, SINR_BIN_KPI, SINR_BIN_SIZE, 'median', sinr_curve_datafile)
    if DT_TYPE == '5G_DT':
        sample_discrete(binning_data, RSRP_BIN_KPI_2, RSRP_BIN_SIZE_2, 'median', rsrp_curve_datafile_2)
        sample_discrete(binning_data, PL_BIN_KPI, PL_BIN_SIZE, 'median', pl_curve_datafile)
        sample_discrete(binning_data, NR_PUSCH_POWER_BIN_KPI, PUSCH_POWER_BIN_SIZE, 'median', nr_pusch_power_datafile)
        # sample_discrete(binning_data, DISTANCE_BIN_KPI, DISTANCE_BIN_SIZE, 'median', distance_datafile)

    statistics_dt_kpi_to_excel(statistics_datafile, binning_data, export_kpi_list_local)

def show_message_box(text, message_type):
    msg = QMessageBox()

    if message_type == "Question":
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Question")
    elif message_type == "Warning":
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Warning")
    elif message_type == "Critical":
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Critical")
    else: # "Information"
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Information")

    msg.setText(text)
    # msg.setInformativeText("This is additional information")
    # msg.setDetailedText("The details are as follows:")
    # msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

    msg.exec_()


class DataProcessMainWindow(QMainWindow):
    """Main Window."""
    def __init__(self, parent=None):
        """Initializer."""
        super().__init__(parent)

        self.dt_data = {}
        self.kpi_map = folium.Map(location=[45.5236, -122.6750], zoom_start=13)

        # syt self.fileList = QStringListModel()
        self.fileList = QListWidget()
        self.setWindowTitle("Data Processing")
        self.resize(1200, 800)
        self.centralWidget = QLabel("Hello, World")
        self.centralWidget.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.setCentralWidget(self.centralWidget)

        self._create_actions()
        self._create_menu_bar()
        self._create_widget()
        self._connect_actions()

    def _create_actions(self):
        # Creating action using the first constructor
        self.importAction = QAction(self)
        self.importAction.setText("&Import...")
        # Creating actions using the second constructor
        self.exportAction = QAction("E&xport...", self)
        self.exitAction = QAction("&Exit", self)
        self.copyAction = QAction("&Copy", self)
        self.pasteAction = QAction("&Paste", self)
        self.cutAction = QAction("C&ut", self)
        self.helpContentAction = QAction("&Help Content", self)
        self.aboutAction = QAction("&About", self)

    def _create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        # Creating menus using a QMenu object
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)
        # Creating menus using a title
        edit_menu = menu_bar.addMenu("&Edit")
        help_menu = menu_bar.addMenu("&Help")
        # file_menu.addMenu("&Import...")
        # file_menu.addMenu("&Exit")

        file_menu.addAction(self.importAction)
        file_menu.addAction(self.exportAction)
        file_menu.addAction(self.exitAction)

    def _connect_actions(self):
        # Connect File actions
        self.importAction.triggered.connect(self.import_data)
        self.exportAction.triggered.connect(self.export_data)

        self.fileList.clicked.connect(self.data_list_item_change)
        self.map_web_view_kpi_list.clicked.connect(self.update_map_kpi)
        # self.fileList.currentItemChanged.connect(self.data_list_item_change)

    def _create_widget(self):
        self.vLayout = QVBoxLayout()
        self.dock = QDockWidget("Data List", self)
        self.dock.setWidget(self.fileList)
        self.addDockWidget(Qt.TopDockWidgetArea, self.dock)

        self.tabWidget = QTabWidget(self.centralWidget)
        # self.vLayout.addWidget(self.tabWidget)
        # self.setLayout(self.vLayout)

        """ Create all data tabs """
        self.tabWidget.setLayoutDirection(Qt.LeftToRight)
        self.tabWidget.setElideMode(Qt.ElideRight)
        self.tabWidget.setTabsClosable(False)
        self.tabWidget.setMovable(True)
        self.tabWidget.setObjectName("TabWidget")
        self.rawDataTab = QtWidgets.QWidget()
        self.rawDataTab.setObjectName("Raw Data")
        self.binnedDataTab = QtWidgets.QWidget()
        self.binnedDataTab.setObjectName("Binned Data")
        self.discreteDataTab = QtWidgets.QWidget()
        self.discreteDataTab.setObjectName("Discrete Data")
        self.mapDataTab = QtWidgets.QWidget()
        self.mapDataTab.setObjectName("Map Data")
        self.tabWidget.addTab(self.rawDataTab, "Raw Data")
        self.tabWidget.addTab(self.binnedDataTab, "Binned Data")
        self.tabWidget.addTab(self.discreteDataTab, "Discrete Data")
        self.tabWidget.addTab(self.mapDataTab, "Map Data")

        """ Create table view on raw data tab """
        self.raw_data_table = QTableView()
        self.raw_data_table_statistics = QTableView()

        self.raw_data_v_layout = QVBoxLayout()
        self.raw_data_v_layout.addWidget(self.raw_data_table)
        self.raw_data_v_layout.addWidget(self.raw_data_table_statistics)
        self.raw_data_v_layout.setStretchFactor(self.raw_data_table, 3)
        self.raw_data_v_layout.setStretchFactor(self.raw_data_table_statistics, 1)
        self.rawDataTab.setLayout(self.raw_data_v_layout)

        """ Create table view on binned data tab """
        self.binned_data_table = QTableView()
        self.binned_data_table_statistics = QTableView()

        self.binned_data_v_layout = QVBoxLayout()
        self.binned_data_v_layout.addWidget(self.binned_data_table)
        self.binned_data_v_layout.addWidget(self.binned_data_table_statistics)
        self.binned_data_v_layout.setStretchFactor(self.binned_data_table, 3)
        self.binned_data_v_layout.setStretchFactor(self.binned_data_table_statistics, 1)
        self.binnedDataTab.setLayout(self.binned_data_v_layout)

        """ Create map view on map data tab """
        self.map_web_view = QWebEngineView()
        self.map_web_view_kpi_list = QListWidget()
        self.map_data_h_layout = QHBoxLayout()
        self.map_data_h_layout.addWidget(self.map_web_view_kpi_list)
        self.map_data_h_layout.addWidget(self.map_web_view)
        self.map_data_h_layout.setStretchFactor(self.map_web_view_kpi_list, 1)
        self.map_data_h_layout.setStretchFactor(self.map_web_view, 3)
        self.mapDataTab.setLayout(self.map_data_h_layout)

        self.setCentralWidget(self.tabWidget)

    def data_list_item_change(self):
        file_name = self.fileList.currentItem().text()
        print("1. file name is: ", file_name)

        self.update_data_view(file_name)

    def update_data_view(self, file_name):
        print("test")
        if file_name is None:
            return

        else:
            print("file name is: ", type(file_name))

            """ Load data on raw data table """
            pandas_model = PandasModel(self.dt_data[file_name][0])
            self.raw_data_table.setModel(pandas_model)
            data_statistics = self.dt_data[file_name][0].describe(percentiles=[0.05, 0.1, 0.5, 0.9, 0.97])
            pandas_model_statistics = PandasModel(data_statistics)
            self.raw_data_table_statistics.setModel(pandas_model_statistics)
            del pandas_model, pandas_model_statistics

            """ Load data on binned data table """
            pandas_model = PandasModel(self.dt_data[file_name][1])
            self.binned_data_table.setModel(pandas_model)
            data_statistics = self.dt_data[file_name][1].describe(percentiles=[0.05, 0.1, 0.5, 0.9, 0.97])
            pandas_model_statistics = PandasModel(data_statistics)
            self.binned_data_table_statistics.setModel(pandas_model_statistics)
            del pandas_model, pandas_model_statistics

            """ Load data on binned data table """
            geoplotting_datafile = os.path.join(os.path.dirname(file_name),
                                                os.path.basename(file_name).split('.')[0] + '_geoplotting.html')

            self.map_web_view_kpi_list.addItems(self.dt_data[file_name][1].columns)
            # self.kpi_map = folium.Map(location=[45.5236, -122.6750], zoom_start=13)
            # sample_plot_on_map(self.kpi_map, self.dt_data[file_name][1], RSRP_BIN_KPI, geoplotting_datafile, '')

            # point_layer = folium.FeatureGroup(name="Query Search")

            for i, v in self.dt_data[file_name][1].iterrows():
                """
                folium.CircleMarker(location=[v['binned_lat'], v['binned_lon']],
                                    radius=1,
                                    # tooltip=popup,
                                    color='#FFBA00',
                                    fill_color='#FFBA00',
                                    fill=True).add_to(self.kpi_map)"""
                """
                self.kpi_map.add_child(folium.CircleMarker(location=[v['binned_lat'], v['binned_lon']],
                                                           radius=1,
                                                           # tooltip=popup,
                                                           color='#FFBA00',
                                                           fill_color='#FFBA00',
                                                           fill=True))"""
                """
                point_layer.add_child(folium.CircleMarker(location=[v['binned_lat'], v['binned_lon']],
                                                          radius=1,
                                                          # tooltip=popup,
                                                          color='#FFBA00',
                                                          fill_color='#FFBA00',
                                                          fill=True)).add_to(self.kpi_map)
                self.kpi_map.add_child(point_layer)"""
                print(v['binned_lat'], v['binned_lon'])

            folium.LayerControl(collapsed=False).add_to(self.kpi_map)
            self.kpi_map.fit_bounds([[self.dt_data[file_name][1]['binned_lat'].min(),
                                      self.dt_data[file_name][1]['binned_lon'].min()],
                                     [self.dt_data[file_name][1]['binned_lat'].max(),
                                      self.dt_data[file_name][1]['binned_lon'].max()]])

            self.kpi_map.save(geoplotting_datafile)

            # self.map_web_view.load(QUrl("file:///"+geoplotting_datafile))
            # m = folium.Map(location=[45.5236, -122.6750], tiles="Stamen Toner", zoom_start=13)
            # m = folium.Map(location=[45.5236, -122.6750], zoom_start=13)

            data = io.BytesIO()
            self.kpi_map.save(data, close_file=False)

            self.map_web_view.setHtml(data.getvalue().decode())

            print("done")

    def update_map_kpi(self):
        file_name = self.fileList.currentItem().text()
        print("1. file name is: ", file_name)

        map_kpi = self.map_web_view_kpi_list.currentItem().text()
        print("2. map kpi is: ", map_kpi)

        point_layer = folium.FeatureGroup(name="Query Search")
        for i, v in self.dt_data[file_name][1].iterrows():
            folium.RegularPolygonMarker(location=[v['binned_lat'], v['binned_lon']],
                                        radius=4,
                                        # tooltip=popup,
                                        color='blue',
                                        fill_color='blue',
                                        fill=True).add_to(self.kpi_map)
            """point_layer.add_child(folium.RegularPolygonMarker(location=[v['binned_lat'], v['binned_lon']],
                                                      radius=1,
                                                      # tooltip=popup,
                                                      color='#FFBA00',
                                                      fill_color='#FFBA00',
                                                      fill=True))
        self.kpi_map.add_child(point_layer)"""
        folium.LayerControl(collapsed=False).add_to(self.kpi_map)

        tmp_file = QTemporaryFile("XXXXXX.html", self)
        if tmp_file.open():
            self.kpi_map.save(tmp_file.fileName())
            url = QUrl.fromLocalFile(tmp_file.fileName())
            self.map_web_view.load(url)

    def import_data(self):
        """ Logic for opening an existing file goes here...
        self.centralWidget.setText("<b>File > Import...</b> clicked")"""
        self.open_filename_dialog()

    def export_data(self):
        """  Logic for opening an existing file goes here...
        self.centralWidget.setText("<b>File > Export...</b> clicked")"""
        pass

    def open_filename_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "",
                                                   "All Files (*);;Python Files (*.py)", options=options)
        if file_name:
            if not self.fileList.findItems(file_name, Qt.MatchExactly):
                item = QListWidgetItem(file_name)
                self.fileList.addItem(item)
                self.fileList.setCurrentItem(item)

                print("onOpenExistingProject: ", self.fileList.currentItem().text())

                raw_data = load_data(file_name, filetype)
                binned_data = sample_spatial_binning(raw_data, AREA_BINNING_SIZE, None, 'mean')

                self.dt_data[file_name] = [raw_data, binned_data]

                self.update_data_view(file_name)

            else:
                show_message_box(file_name + " has been loaded.", "Information")


class PandasModel(QAbstractTableModel):

    """A model to interface a Qt view with pandas dataframe """

    def __init__(self, dataframe: pd.DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=QModelIndex()) -> int:
        """ Override method from QAbstractTableModel

        Return row count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe)

        return 0

    def columnCount(self, parent=QModelIndex()) -> int:
        """Override method from QAbstractTableModel

        Return column count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe.columns)
        return 0

    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
        """Override method from QAbstractTableModel

        Return data cell from the pandas DataFrame
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return str(self._dataframe.iloc[index.row(), index.column()])

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ):
        """Override method from QAbstractTableModel

        Return dataframe index as vertical header data and columns as horizontal header data.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])

            if orientation == Qt.Vertical:
                return str(self._dataframe.index[section])

        return None


if __name__ == '__main__':

    # best_ssv_avg_data, best_ssv_avg_timestamp = calculate_best_avg_ssv_kpi(data, XCAL_TIME_STAMP,
    # SSV_DL_THROUGHPUT_KPI,
    #                                                                       SSV_THROUGHPUT_PERIOD)

    # best_ssv_max_data, best_ssv_max_timestamp = calculate_best_avg_ssv_kpi(data, XCAL_TIME_STAMP,
    # SSV_DL_THROUGHPUT_KPI,
    #                                                                       1)

    # data_all = pd.concat([best_ssv_avg_data.mean().to_frame().transpose(), best_ssv_max_data])
    # write_data_to_excel(result_output_file, 'Result', data_all, endc_ssv_dl_thp_export_list)

    # plot_ssv_kpi_to_pdf(result_output_file_charts, data, XCAL_TIME_STAMP, endc_ssv_dl_thp_export_list,
    # best_ssv_avg_timestamp, SSV_THROUGHPUT_PERIOD)
    # ssv_kpi_summary(trace_folder)

    app = QApplication(sys.argv)
    win = DataProcessMainWindow()
    win.show()
    sys.exit(app.exec_())
    # drive_test_post_process(dt_trace)




