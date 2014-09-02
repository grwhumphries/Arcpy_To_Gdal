print ("Startup... modules importing... please wait")
import os
import os.path
import glob
import subprocess
import datetime
import base64
import csv
import shutil
import psutil
import six
import pyparsing
import pytz                         #MUST BE INSTALLED
import numpy                        #MUST BE INSTALLED
import matplotlib.pyplot as plt     #MUST BE INSTALLED
import matplotlib.image as mpimg
from PyQt4 import QtCore, QtGui     #MUST BE INSTALLED
from pandas import DataFrame        #MUST BE INSTALLED
from PIL import Image, ImageTk
from Tkinter import *
from multiprocessing import Process
from time import sleep
print ("----------------------------------------------------------------------")

from arcfunctions import ArcFunctions


################################################################################
""" Sets the Configuration class to configure the self dictionary """

class Config(object):

# Creates dictionary object (relational list)

    def __init__(self, filename='core.cfg'):
        self.dict = {}
        self.filename = filename
        try:
            lines = open(filename).readlines()
            for line in lines:
                try:
                    # Splits the line into the first and second part
                    # and assigns variables

                    key, value = line.strip().split('=')
                    self.dict[key] = value
                except ValueError:
                    pass
        except IOError:
            pass

    def get(self, key, default):
        value = self.dict.get(key, default)
        if type(value) != type(default):
            value = type(default)(value)
        self.dict[key] = value
        return value

    def set(self, key, value):
        self.dict[key] = value

    def save(self):
        f = open(self.filename, "w")
        for key in self.dict:
            f.write(key + '=' + str(self.dict[key]) + '\n')
        f.close()
################################################################################

""" Set the Reporter class which runs all the functions """

class Reporter(object):

    def __init__(self, config, pa_file, workspace, output_space, resolution, spm):
        """Initialize reporter"""
        self.config = config
        self.shape = pa_file
        self.env_workspace = workspace
        self.output_space = output_space
        self.resolution = float(resolution)
        self.spmpath = spm

        self.raster_list = a.init_lists(self.env_workspace)
        self.init_dirs()

    def init_dirs(self):
        """Create Init output directory based on date and time"""
        i = datetime.datetime.now()
        CurrentTime = i.isoformat()
        CurrentTime = CurrentTime.replace(":","")
        self.Output_path = os.path.join(self.output_space,CurrentTime)
        if not os.path.exists(self.Output_path):
            os.makedirs(self.Output_path)
            self.Mapdir = os.path.join(self.Output_path,"Maps")
            self.Grovdir = os.path.join(self.Output_path,"Groves")
            self.Scoredir = os.path.join(self.Output_path,"Scored")
            os.makedirs(self.Mapdir)
            os.makedirs(self.Grovdir)
            os.makedirs(self.Scoredir)

        # SEE BELOW
        """When updating this code, this must be changed"""
        self.pypath = os.path.dirname(os.path.realpath("ENM_SPM_V1.0.py"))
        self.mxdpath = os.path.join(self.pypath,"Blank.mxd")
        # CHANGE ABOVE

    def report(self):
        """Main report function"""
        print (a.overlay(self.raster_list,self.env_workspace,self.shape))
        print("Creating background points for predictions...")
        self.background_points = a.background(self.Output_path,self.resolution,self.raster_list,self.env_workspace)
        print("Background data sampled")
        print("--------------------------------------------------------------")

        start = self.shape.rfind("/")+1
        csvName = self.shape[start:-4]+".csv"
        self.data = os.path.join(self.Output_path,csvName)
        self.grid_data = self.background_points[:-4]+".csv"

        print(a.csvwriter(self.shape,self.background_points,self.data,self.grid_data))



        self.cleaner()

        self.N = True
        f1 = Process(target = self.run_spm())
        f2 = Process(target = self.Test_loops())

        f2.start()
        f1.start()




    def cleaner(self):
        """This function will clean the .csv file for analysis by removing
        non-data values and replacing with NAs. Non-data values are those
        defined as values = 0, = -999, = -9999, or <= -34,000 """

        # Uses the clean function defined below to remove nodata values
        print("Cleaning CSV files of nodata values")
        Output = os.path.join(self.Output_path,"model_data_MODEL_WITH_ME.csv")
        self.clean(self.data,Output)

        self.cleanedgrid = os.path.join(self.Output_path,
                                "background_data_SCORE_ME_TO_CREATE_MAP.csv")
        self.clean(self.grid_data,self.cleanedgrid)

        os.remove(self.grid_data)
        os.remove(self.data)

        print("Cleaning complete")
        print("---------------------------------------------------------------")


    def clean(self,Input,Output):
        """ Cleans the csv files of no-data values for use in analysis in SPM"""
        X = csv.reader(open(Input,"rb"))
        f = open(Output,"wb")
        Y = csv.writer(f)
        lines = [l for l in X]
        rn = 0
        for row in lines:
            lines[rn][0] = rn
            for column in range(3,len(lines[rn])):
                if lines[rn][column] == '0.000000' or lines[rn][column] == '-999.000000'or lines[rn][column] == '-9999.000000':
                    lines[rn][column] = ''
            rn += 1
        Y.writerows(lines)
        f.close()

    def run_spm(self):
        """This function opens the SPM program without the blocks caused
        by os.system or subprocess.call. This is defined as a separate function
        in order to create a multi-process """

        Spath = os.path.join(self.spmpath,'bin/SPM.exe')
        os.startfile(Spath)


        """ Create Option in GUI to point to SPM in program files or
            program files (x86) as default """


    def SPM_test(self):
        """This function will test to see if SPM is running.. if still running
        it will continue to look for the output files to create maps"""
        proc_names={}
        for p in list(psutil.process_iter()):
            try:
                proc_names[p.pid] = p.name()
            except psutil.Error:
                pass
        self.N = 'SPM.exe' in proc_names.values()

    def List_difference(self):
        """ This function determines if a new scored file has been created and
        then copies to a new folder where it will be used to create the map jpeg"""

        #""" Directory monitoring through WINDOWS """ Done through OS

        os.chdir(self.Scoredir)
        ScoreCSVs = glob.glob('*.csv')
        os.chdir(self.Mapdir)
        MapCSVs = glob.glob('*.csv')
        LIST = list(set(ScoreCSVs).difference(set(MapCSVs)))

        if len(LIST) == 1:
            try:
                self.oldfile = os.path.join(self.Scoredir,LIST[0])
                self.newfile = os.path.join(self.Mapdir,LIST[0])
                score = DataFrame.from_csv(self.oldfile,sep=",")
                grid = DataFrame.from_csv(self.cleanedgrid,sep=",")
                merged = score.join(grid)
                merged.to_csv(self.newfile)
                Test = True
            except:
                Test = False
            if Test == True:

                self.out_Layer = os.path.split(self.newfile)[1][:-4]
                self.gridshape = self.out_Layer+".shp"
                self.rastername = self.out_Layer+".img"
                print ("PLEASE WAIT.. setting up parameters to build map...")
                print ("This may take time if resolution of output is high")
                print ("----------")
                self.SpRf = a.grid_create(self.out_Layer,self.gridshape,self.rastername,self.newfile,self.Mapdir,self.shape)
                print ("Grid created")
                print ("------------------------------------------------------")

                self.outIDWname = os.path.join(self.Mapdir, self.rastername)
                self.outJPEG = a.map_maker(self.resolution,self.gridshape,self.SpRf,self.outIDWname,self.out_Layer,self.Mapdir,self.mxdpath,self.rastername)
                self.viewer()

        else:
            pass

    def viewer():
        print("Jpeg created... opening")
        print("")
        print("Please close the JPEG window before creating next model")
        img = mpimg.imread(self.outJPEG)
        lum_img = img[:,:,0]
        imgplot = plt.imshow(lum_img)
        imgplot.set_cmap('hot')
        plt.show()
        print ("--------------------------------------------------------------")


    def Test_loops(self):
        """This function creates the maps for output"""
        self.N = True
        while self.N == True:
            self.SPM_test()
            self.List_difference()
            sleep(1)


###############################################################################
""" Below is the App class to run the GUI """

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class App(QtGui.QMainWindow):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(741, 359)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))

        # Species occurrences
        self.pushButton = QtGui.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(280, 130, 161, 21))
        self.pushButton.setObjectName(_fromUtf8("pushButton"))

        self.lineEdit = QtGui.QLineEdit(self.centralwidget)
        self.lineEdit.setGeometry(QtCore.QRect(460, 130, 231, 20))
        self.lineEdit.setObjectName(_fromUtf8("lineEdit"))

        # Output Directory
        self.pushButton_2 = QtGui.QPushButton(self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(280, 160, 161, 21))
        self.pushButton_2.setObjectName(_fromUtf8("pushButton_2"))

        self.lineEdit_2 = QtGui.QLineEdit(self.centralwidget)
        self.lineEdit_2.setGeometry(QtCore.QRect(460, 160, 231, 20))
        self.lineEdit_2.setObjectName(_fromUtf8("lineEdit_2"))

        # Environmental Layers
        self.pushButton_3 = QtGui.QPushButton(self.centralwidget)
        self.pushButton_3.setGeometry(QtCore.QRect(280, 190, 161, 21))
        self.pushButton_3.setObjectName(_fromUtf8("pushButton_3"))

        self.lineEdit_3 = QtGui.QLineEdit(self.centralwidget)
        self.lineEdit_3.setGeometry(QtCore.QRect(460, 190, 231, 20))
        self.lineEdit_3.setObjectName(_fromUtf8("lineEdit_3"))

        # Set SPM location
        self.pushButton_5 = QtGui.QPushButton(self.centralwidget)
        self.pushButton_5.setGeometry(QtCore.QRect(280, 220, 161, 21))
        self.pushButton_5.setObjectName(_fromUtf8("pushButton_5"))

        self.lineEdit_5 = QtGui.QLineEdit(self.centralwidget)
        self.lineEdit_5.setGeometry(QtCore.QRect(460, 220, 231, 20))
        self.lineEdit_5.setObjectName(_fromUtf8("lineEdit_5"))


        # Resolution
        self.lineEdit_4 = QtGui.QLineEdit(self.centralwidget)
        self.lineEdit_4.setGeometry(QtCore.QRect(460, 80, 51, 20))
        self.lineEdit_4.setObjectName(_fromUtf8("lineEdit_4"))

        # Run program
        self.pushButton_4 = QtGui.QPushButton(self.centralwidget)
        self.pushButton_4.setGeometry(QtCore.QRect(380, 250, 141, 61))
        font = QtGui.QFont()
        font.setPointSize(14)
        palette = QtGui.QPalette(self.pushButton_4.palette())
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor('red'))
        self.pushButton_4.setPalette(palette)
        self.pushButton_4.setFont(font)
        self.pushButton_4.setObjectName(_fromUtf8("pushButton_4"))


        # Horizontal Line
        self.line = QtGui.QFrame(self.centralwidget)
        self.line.setGeometry(QtCore.QRect(280, 110, 411, 16))
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))

        # Output resolution label
        self.label = QtGui.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(320, 80, 131, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))

        # Title label
        self.label_2 = QtGui.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(230, 10, 311, 51))
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("Times New Roman"))
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.label_2.setFont(font)
        self.label_2.setObjectName(_fromUtf8("label_2"))

        # Signature label
        self.label_3 = QtGui.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(50, 250, 141, 61))
        font = QtGui.QFont()
        font.setPointSize(7)
        self.label_3.setFont(font)
        self.label_3.setObjectName(_fromUtf8("label_3"))

        # Mainwindow functions
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 741, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        # Open translate UI
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Salford Ecological Niche Modeling", None))
        self.pushButton.setText(_translate("MainWindow", "Species occurrences", None))
        self.pushButton.clicked.connect(self.shapespace)

        self.pushButton_2.setText(_translate("MainWindow", "Output directory", None))
        self.pushButton_2.clicked.connect(self.output)

        self.pushButton_3.setText(_translate("MainWindow", "Environmental layers", None))
        self.pushButton_3.clicked.connect(self.envspace)

        self.lineEdit_4.setText(_translate("MainWindow", "1.000", None))
        self.pushButton_4.setText(_translate("MainWindow", "RUN SCRIPT", None))
        self.pushButton_4.clicked.connect(self.go)

        self.pushButton_5.setText(_translate("MainWindow", "Salford root directory", None))
        self.lineEdit_5.setText("C:/Program Files (x86)/Salford Systems/") #_translate("MainWindow",, None)
        self.pushButton_5.clicked.connect(self.spmpath)

        self.label.setText(_translate("MainWindow", "Output Resolution", None))
        self.label_2.setText(_translate("MainWindow", "Welcome to the Salford Systems\n"
"Ecological Niche Modeling Package", None))
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_3.setText(_translate("MainWindow", "This script was written by\n"
" Grant Humphries, August 2014\n"
" for Salford Systems ltd.", None))
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)


    def shapespace(self):
        self.lineEdit.setText("")
        dirname = str(QtGui.QFileDialog.getOpenFileName(self,'Please select the file for modeling', 'C:/', '*.shp'))
        if len(dirname ) > 0:
            self.lineEdit.setText(dirname)

    def output(self):
        self.lineEdit_2.setText("")
        dirname = str(QtGui.QFileDialog.getExistingDirectory(self,'Please select where you would like your output to be stored',"C:/"))
        if len(dirname ) > 0:
            self.lineEdit_2.setText(dirname)

    def envspace(self):
        self.lineEdit_3.setText("")
        dirname = str(QtGui.QFileDialog.getExistingDirectory(self,'Please select the directory where your environmental layers are stored',"C:/"))
        if len(dirname ) > 0:
            self.lineEdit_3.setText(dirname)
            print ("Checking directory...")

            ws = str(self.lineEdit_3.text())
            rlist = a.init_lists(ws)

            if len(rlist) == 0:
                QtGui.QMessageBox.critical(self,"Error!" , 'Sorry, this directory contains no raster layers',QtGui.QMessageBox.Ok)
            else:
                print ("Okay!")
                print ("---------")

    def spmpath(self):
            dirname = str(QtGui.QFileDialog.getExistingDirectory(self,'Please select Salford Systems root folder',"C:/"))
            if len(dirname ) > 0:
                self.lineEdit_5.setText("")
                self.lineEdit_5.setText(dirname)

    """This is where the model is run - when the users selects "Run Script"""

    def go(self):

        t = datetime.datetime.now()
        SPM_RUNNING = False

        print("Program started at %s:%s:%s" % (t.hour,t.minute,t.second)+" on %s/%s/%s" % (t.day,t.month,t.year) )
        config = Config()
        print("-------------------------------------------------------------------")
        print("Please note, users must create directories in advance, and process all presence / absence points as per documentation")
        print("-------------------------------------------------------------------")


        arg1 = str(self.lineEdit.text())    #Shapefile
        arg2 = str(self.lineEdit_3.text())  #Environmental layers
        arg3 = str(self.lineEdit_2.text())  #Output directory
        arg4 = str(self.lineEdit_4.text())  #Resolution
        arg5 = str(self.lineEdit_5.text())  #Salford root folder


        ##################################################################



        UnitName = a.getsprf(arg1)

        message = "Your output resolution will be "+arg4+" x "+arg4+" "+UnitName+"s.\n Is this correct?"
        reply = QtGui.QMessageBox.question(self,"Resolution confirmation",message,QtGui.QMessageBox.Yes,QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:

            Spath = os.path.join(arg5,'bin/SPM.exe')

            if os.path.exists(Spath):
                reporter = Reporter(config, arg1, arg2, arg3, arg4, arg5)
                reporter.report()
                config.save()

                t2 = datetime.datetime.now()
                print("Program finished at %s:%s:%s" % (t2.hour,t2.minute,t2.second)+" on %s/%s/%s" % (t2.day,t2.month,t2.year) )
                t3 = t2 - t
                dec_mins = str(float(t3.seconds)/60)
                fnd = dec_mins.rfind(".")
                mins = dec_mins[:fnd]
                dec_mins_2 = float(dec_mins[fnd:])
                secs = round(dec_mins_2*60,2)
                print("")
                print("Total time was "+str(mins)+" minutes and "+str(secs)+" seconds.")
                print("")
                print("Thanks for downloading and running this script")
                print("-----------------------------------------------------------")
                print("")
                raw_input("Press any key to exit")

            else:
                QtGui.QMessageBox.critical(self,"Error!" , 'Sorry, I cannot find SPM.exe, please locate on disk',QtGui.QMessageBox.Ok)

        else:
            pass

################################################################################
""" Run the program, starting with the GUI to call everything else """

if __name__ == "__main__":
    import sys
    a = ArcFunctions()

    app = QtGui.QApplication(sys.argv)
    MainWindow = QtGui.QMainWindow()
    pic = QtGui.QLabel(MainWindow)
    pic.setGeometry(QtCore.QRect(10, 110, 261, 71))
    pm = QtGui.QPixmap()

    icon='''
    R0lGODlh+gBLAPcAAAAAAP///0BAQDQ0NLy93LGz18zN5dDR54KHvoWKwJGVxZaayZqeyp2hzaSn
    z6qt066x1be627S318DC38TG4dzd7N/g7nB3s3N5tXJ4tHR7tXd9t3h+t3+FvImOwY2Sw6Ckzqaq
    0bK22cDD4MfK49PV6dbY6mBqrGVurWdwrmlysGtzsW52snmAuHyDunuCuH2FupSaxrzA3VVhpldj
    p1llp1tmqF1pqmBqq2JtrGJtq2t1sUlXoExaoU5co09do1FfpFJgpVZjp4aQwEFSnERVnkZYoEla
    oXuHujBGlTdNmTtPmj1Rmz9UnT9TnUJVnUVYnypDkzJKljVMmDhPmmJ1r3OEuIORvyE+jyVCkixH
    lS5JlUdgo1Bmp22AtXOFt3qLu4uaxAwwiBI1ixY4jRo7jh09jyBAkShGlSxLmDFPmT5ZoENdoVx0
    sGJ5sWh+tHWKvAMpgzpYn01oplpzrXyRwHyQvoWZxOLq9efx+trp9qzO6K7Q6rTT6rnW7L7Z7sfe
    8M7i8u31+3qz2Y+/4JXC4pnF46PK5qnN5/L4/GOp1Ger1Gqs1W6u13Gw13Ox13ay2Xm02n212n+3
    24K424a73Yu93o7A4J3I5Fmm0l+o02Kp0mSq02et1QB4tQB1swh8twt+uBKDuyCKvzuczECZxkOf
    zUuhz1CizlWl0GGs022y13m52wCCvACBugB+uAB8twV9tw+Euy2SwzGbyzOVxEylz1+w13zA3gCK
    wQCHwACJwACFvgCHvgCHvQCFvQOIwBqWyCKYyTyn0Vat0wCMwgGOwwSPxASPwwiRxg+Ux0Ss03G8
    2Pv+/v7+/v39/fv7+/j4+Pf39/T09PHx8ezs7OXl5eLi4uDg4Nzc3NbW1tHR0czMzMnJycbGxsPD
    w7+/v7y8vLq6urS0tKqqqqWlpaOjo56enpSUlIyMjIKCgnl5eWhoaGBgYFZWVkpKSkdHR0NDQ0FB
    QT09PTg4ODY2NjExMS0tLSoqKiYmJiEhIRcXFwoKCgUFBQICAv///yH5BAEAAP8ALAAAAAD6AEsA
    AAj/AP8JHEiwoMGDCBMqXMiwocOHECNKnEixosWLGDNq3Mixo8ePIEOKHEmypMmTKFOqXMmypcuX
    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
    ABQwAV9hE4O7uIzbuI77uJAbuZI7uRIREAA7
    '''


    pm.loadFromData(base64.b64decode(icon))
    pic.setPixmap(pm)
    ui = App()
    ui.setupUi(MainWindow)
    MainWindow.show()
    app.exec_()













