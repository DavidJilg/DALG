# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'WelcomeScreen.ui'
##
## Created by: Qt User Interface Compiler version 6.4.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QFrame, QLabel, QPushButton,
    QSizePolicy, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(757, 499)
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(280, 441, 201, 60))
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.buttonBox.sizePolicy().hasHeightForWidth())
        self.buttonBox.setSizePolicy(sizePolicy)
        self.buttonBox.setAutoFillBackground(False)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)
        self.buttonBox.setCenterButtons(True)
        self.checkBox = QCheckBox(Dialog)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setGeometry(QRect(20, 460, 251, 23))
        font = QFont()
        font.setPointSize(12)
        self.checkBox.setFont(font)
        self.open_manual_button = QPushButton(Dialog)
        self.open_manual_button.setObjectName(u"open_manual_button")
        self.open_manual_button.setGeometry(QRect(630, 459, 111, 27))
        self.label_welcome_screen_title = QLabel(Dialog)
        self.label_welcome_screen_title.setObjectName(u"label_welcome_screen_title")
        self.label_welcome_screen_title.setGeometry(QRect(40, 15, 681, 51))
        font1 = QFont()
        font1.setFamilies([u"Yu Gothic Light"])
        font1.setPointSize(20)
        self.label_welcome_screen_title.setFont(font1)
        self.label_welcome_screen_title.setTextFormat(Qt.AutoText)
        self.label_welcome_screen_title.setAlignment(Qt.AlignCenter)
        self.line = QFrame(Dialog)
        self.line.setObjectName(u"line")
        self.line.setGeometry(QRect(0, 70, 761, 16))
        self.line.setFrameShadow(QFrame.Plain)
        self.line.setLineWidth(1)
        self.line.setFrameShape(QFrame.HLine)
        self.line_2 = QFrame(Dialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setGeometry(QRect(0, 430, 761, 16))
        self.line_2.setFrameShadow(QFrame.Plain)
        self.line_2.setLineWidth(1)
        self.line_2.setFrameShape(QFrame.HLine)
        self.label_5 = QLabel(Dialog)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(20, 370, 711, 61))
        font2 = QFont()
        font2.setPointSize(13)
        self.label_5.setFont(font2)
        self.label_5.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.label_5.setWordWrap(True)
        self.label_6 = QLabel(Dialog)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setGeometry(QRect(20, 90, 711, 131))
        self.label_6.setFont(font2)
        self.label_6.setTextFormat(Qt.RichText)
        self.label_6.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.label_6.setWordWrap(True)
        self.label_6.setOpenExternalLinks(True)
        self.label_7 = QLabel(Dialog)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setGeometry(QRect(20, 215, 711, 151))
        self.label_7.setFont(font2)
        self.label_7.setTextFormat(Qt.RichText)
        self.label_7.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.label_7.setWordWrap(True)
        self.label_7.setOpenExternalLinks(True)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Welcome!", None))
        self.checkBox.setText(QCoreApplication.translate("Dialog", u"Do not show this screen again.", None))
        self.open_manual_button.setText(QCoreApplication.translate("Dialog", u"Open Manual", None))
        self.label_welcome_screen_title.setText(QCoreApplication.translate("Dialog", u"Welcome to DALG: The Data Aware Event Log Generator!", None))
        self.label_5.setText(QCoreApplication.translate("Dialog", u"You can open this welcome screen again after it has been closed by pressing \"F2\" or choosing the \"Help -> Show Welcome Screen Again\" option in the top menu bar.", None))
        self.label_6.setText(QCoreApplication.translate("Dialog", u"<html><head/><body><p>This software allows you to generate event logs that conform to the data and the control-flow perspective of a provided Data Petri net by using the <a href=\"https://pods4h.com/wp-content/uploads/2022/10/PODS4H_2022_paper_145_Gruger_Sample.pdf\"><span style=\" text-decoration: underline; color:#0000ff;\">SAMPLE</span></a> approach. The software was originally developed by <a href=\"https://www.linkedin.com/in/david-jilg-b43bb119b/\"><span style=\" text-decoration: underline; color:#0000ff;\">David Jilg</span></a> as part of his <a href=\"http://dx.doi.org/10.13140/RG.2.2.35331.78880\"><span style=\" text-decoration: underline; color:#0000ff;\">Master Thesis</span></a> and is currently actively developed by researchers at the <a href=\"https://www.uni-trier.de/en/universitaet/fachbereiche-faecher/fachbereich-iv/faecher/informatikwissenschaften/professuren/wirtschaftsinformatik-2/chair\"><span style=\" text-decoration: underline; color:#0000ff;\">Chair of Business Information Systems II</sp"
                        "an></a> at the <a href=\"https://www.uni-trier.de/en/\"><span style=\" text-decoration: underline; color:#0000ff;\">University of Trier</span></a>. </p></body></html>", None))
        self.label_7.setText(QCoreApplication.translate("Dialog", u"<html><head/><body><p>It is strongly recommended that you read the manual that is provided with this software before using it. You can open the manual right here in the welcome screen by pressing the &quot;Open Manual&quot; button. Alternatively you can open the manual after you have closed this screen by pressing &quot;F1&quot; or using the &quot;Help -&gt; Open User Manual&quot; option in the top menu bar. If for whatever reason the opening of the manual does not work you can always find the updated manual in the github repository: <a href=\"https://github.com/DavidJilg/DALG\"><span style=\" text-decoration: underline; color:#0000ff;\">github.com/DavidJilg/DALG</span></a>. </p></body></html>", None))
    # retranslateUi

