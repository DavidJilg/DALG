# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'IncludedVariablesInput.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QLabel, QSizePolicy,
    QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(243, 24)
        self.name_label = QLabel(Form)
        self.name_label.setObjectName(u"name_label")
        self.name_label.setGeometry(QRect(10, 0, 141, 21))
        font = QFont()
        font.setPointSize(12)
        self.name_label.setFont(font)
        self.name_label.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.check_box_input = QCheckBox(Form)
        self.check_box_input.setObjectName(u"check_box_input")
        self.check_box_input.setGeometry(QRect(200, 0, 21, 23))

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
#if QT_CONFIG(tooltip)
        self.name_label.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>This setting allows to set a transition to be invisible. Invisible transitions are do not appear in the event log but do influence the control flow of the model.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.name_label.setText(QCoreApplication.translate("Form", u"NAME", None))
#if QT_CONFIG(tooltip)
        self.check_box_input.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>This setting allows to set a transition to be invisible. Invisible transitions are do not appear in the event log but do influence the control flow of the model.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.check_box_input.setText("")
    # retranslateUi

