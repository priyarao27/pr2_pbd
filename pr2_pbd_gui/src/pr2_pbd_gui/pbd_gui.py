#!/usr/bin/env python

import roslib
roslib.load_manifest('pr2_pbd_gui')
roslib.load_manifest('speech_recognition')
roslib.load_manifest('speakeasy');
roslib.load_manifest('sound_play');


import os
from subprocess import call

# ROS libraries
import rospy
from std_msgs.msg import String
#import qt_gui.qt_binding_helper
from qt_gui.plugin import Plugin
from python_qt_binding import QtGui,QtCore
from python_qt_binding.QtGui import QWidget, QFrame, QGroupBox, QIcon
from python_qt_binding.QtCore import Slot, qDebug, QSignalMapper, QTimer, qWarning, Signal
from speakeasy.msg import SpeakEasyTextToSpeech
from speech_recognition.msg import Command
from sound_play.msg import SoundRequest


class ClickableLabel(QtGui.QLabel):
    def __init__(self, parent, index, clickCallback):
        QtGui.QLabel.__init__(self, parent)
        self.index = index
        self.clickCallback = clickCallback
    
    def mousePressEvent(self, event):
        self.emit(QtCore.SIGNAL('clicked()'), "Label pressed")
        self.clickCallback(self.index)

class ActionIcon(QtGui.QGridLayout):
    def __init__(self, parent, index, clickCallback):
        QtGui.QGridLayout.__init__(self)
        path = os.popen('rospack find pr2_pbd_gui').read()
        path = path[0:len(path)-1]
        self.notSelectedIconPath = path + '/icons/actions0.png'
        self.selectedIconPath = path + '/icons/actions1.png'
        self.selected = True
        self.actionIconWidth = 50
        self.index = index
        self.icon = ClickableLabel(parent, index, clickCallback)
        self.text = QtGui.QLabel(parent)
        self.text.setText(self.getName())
        self.updateView()
        self.addWidget(self.icon, 0, 0)
        self.addWidget(self.text, 1, 0)
    
    def getName(self):
        return 'Action' + str(self.index + 1)
    
    def updateView(self):
        if self.selected:
            pixmap = QtGui.QPixmap(self.selectedIconPath)
        else:
            pixmap = QtGui.QPixmap(self.notSelectedIconPath)
        self.icon.setPixmap(pixmap.scaledToWidth(self.actionIconWidth, QtCore.Qt.SmoothTransformation))


class StepIcon(QtGui.QGridLayout):
    def __init__(self, parent, index, clickCallback):
        QtGui.QGridLayout.__init__(self)
        path = os.popen('rospack find pr2_pbd_gui').read()
        path = path[0:len(path)-1]
        self.notSelectedIconPath = path + '/icons/node0.png'
        self.selectedIconPath = path + '/icons/node1.png'
        self.notSelectedFirstIconPath = path + '/icons/firstnode0.png'
        self.selectedFirstIconPath = path + '/icons/firstnode1.png'
        self.selected = True
        self.actionIconWidth = 50
        self.index = index
        self.icon = ClickableLabel(parent, index, clickCallback)
        self.text = QtGui.QLabel(parent)
        self.text.setText(self.getName())
        self.updateView()
        self.addWidget(self.icon, 0, 0)
        self.addWidget(self.text, 1, 0)
    
    def getName(self):
        return 'Step' + str(self.index + 1)
    
    def updateView(self):
        if self.index == 0:
            if self.selected:
                pixmap = QtGui.QPixmap(self.selectedIconPath)
            else:
                pixmap = QtGui.QPixmap(self.notSelectedIconPath)
        else:
            if self.selected:
                pixmap = QtGui.QPixmap(self.selectedFirstIconPath)
            else:
                pixmap = QtGui.QPixmap(self.notSelectedFirstIconPath)
            
        self.icon.setPixmap(pixmap.scaledToWidth(self.actionIconWidth, QtCore.Qt.SmoothTransformation))
        
        
        
class PbDGUI(Plugin):

    newCommand = Signal(Command)

    def __init__(self, context):
        super(PbDGUI, self).__init__(context)
        self.setObjectName('PbDGUI')
        self._widget = QWidget()
        self.getCommandList()
        self.commandOutput = rospy.Publisher('recognized_command', Command)
        rospy.Subscriber('recognized_command', Command, self.speechCommandReceived)
        self.speechInput = rospy.Subscriber('speakeasy_text_to_speech_req', SpeakEasyTextToSpeech, self.robotSpeechReceived)
        self.soundInput = rospy.Subscriber('robotsound', SoundRequest, self.robotSoundReceived)
        self.stateInput = rospy.Subscriber('interaction_state', String, self.robotStateReceived)
        QtGui.QToolTip.setFont(QtGui.QFont('SansSerif', 10))
        self.newCommand.connect(self.respondToCommand)
        
        self.commandButtons = dict()
        self.commandButtons[Command.CREATE_NEW_ACTION] = 'New action'
        self.commandButtons[Command.TEST_MICROPHONE] = 'Test microphone'
        self.commandButtons[Command.NEXT_ACTION] = 'Next action'
        self.commandButtons[Command.PREV_ACTION] = 'Prev action'
        self.commandButtons[Command.SAVE_POSE] = 'Save pose'
        self.currentAction = -1

        allWidgetsBox = QtGui.QGridLayout()

        actionBox = QGroupBox('Actions', self._widget)
        self.actionGrid = QtGui.QGridLayout()
        for i in range(6):
            self.actionGrid.addItem(QtGui.QSpacerItem(90, 90), 0, i)
        self.actionIcons = dict()
        actionBoxLayout = QtGui.QHBoxLayout()
        actionBoxLayout.addLayout(self.actionGrid)
        actionBox.setLayout(actionBoxLayout)
        allWidgetsBox.addWidget(actionBox, 0, 0)
        
        actionButtonGrid = QtGui.QGridLayout()
        for i in range(9):
            actionButtonGrid.addItem(QtGui.QSpacerItem(60, 20), 0, i)
        actionButtonGrid.addItem(QtGui.QSpacerItem(60, 20), 1, 0)
        btn = QtGui.QPushButton(self.commandButtons[Command.CREATE_NEW_ACTION], self._widget)
        btn.clicked.connect(self.commandButtonPressed)
        actionButtonGrid.addWidget(btn, 0, 0)
        allWidgetsBox.addLayout(actionButtonGrid, 1, 0)
        
        self.stepsBox = QGroupBox('No actions created yet', self._widget)
        self.stepsGrid = QtGui.QGridLayout()
        for i in range(9):
            self.stepsGrid.addItem(QtGui.QSpacerItem(48, 48), 0, i)
        self.actionSteps = dict()
        stepsBoxLayout = QtGui.QHBoxLayout()
        stepsBoxLayout.addLayout(self.stepsGrid)
        self.stepsBox.setLayout(stepsBoxLayout)
        allWidgetsBox.addWidget(self.stepsBox, 2, 0)
        
        stepsButtonGrid = QtGui.QGridLayout()
        for i in range(9):
            stepsButtonGrid.addItem(QtGui.QSpacerItem(60, 20), 0, i)
        stepsButtonGrid.addItem(QtGui.QSpacerItem(60, 20), 1, 0)
        btn = QtGui.QPushButton(self.commandButtons[Command.SAVE_POSE], self._widget)
        btn.clicked.connect(self.commandButtonPressed)
        stepsButtonGrid.addWidget(btn, 0, 0)
        allWidgetsBox.addLayout(stepsButtonGrid, 3, 0)
        
        
        # Add buttons for sending speech commands
#        commandsGroupBox = QGroupBox('Speech Commands', self._widget)
#        commandsGroupBox.setObjectName('CommandsGroup')
#        grid = QtGui.QGridLayout()
#        nColumns = 4
#        nCommands = len(self.commandList)
#        for i in range(0, nCommands):
#            btn = QtGui.QPushButton(self.commandList[i], self._widget)
#            btn.clicked.connect(self.commandButtonPressed)
#            grid.addWidget(btn, int(i/nColumns), i%nColumns)        
#        
#        commandBox = QtGui.QHBoxLayout()
#        commandBox.addLayout(grid)
#        commandsGroupBox.setLayout(commandBox)

        # Add a display of what the robot says
        speechGroupBox = QGroupBox('Robot Speech', self._widget)
        speechGroupBox.setObjectName('RobotSpeechGroup')
        speechBox = QtGui.QHBoxLayout()
        self.speechLabel = QtGui.QLabel('Robot has not spoken yet')
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Foreground,QtCore.Qt.blue)
        self.speechLabel.setPalette(palette)
        speechBox.addWidget(self.speechLabel)
        speechGroupBox.setLayout(speechBox)

        # Add a display of what the robot says
        stateGroupBox = QGroupBox('Robot State', self._widget)
        stateGroupBox.setObjectName('RobotStateGroup')
        stateBox = QtGui.QHBoxLayout()
        self.stateLabel = QtGui.QLabel('Robot state not received yet.\n\n\n')
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Foreground,QtCore.Qt.red)
        self.stateLabel.setPalette(palette)
        stateBox.addWidget(self.stateLabel)
        stateGroupBox.setLayout(stateBox)

        # Add all children widgets into the main widget
        #allWidgetsBox.addWidget(commandsGroupBox, 1, 0)
        allWidgetsBox.addWidget(speechGroupBox, 5, 0)
        allWidgetsBox.addWidget(stateGroupBox, 6, 0)
        
        
        miscButtonGrid = QtGui.QGridLayout()
        for i in range(6):
            miscButtonGrid.addItem(QtGui.QSpacerItem(60, 20), 0, i)
        miscButtonGrid.addItem(QtGui.QSpacerItem(60, 20), 1, 0)
        btn = QtGui.QPushButton(self.commandButtons[Command.TEST_MICROPHONE], self._widget)
        btn.clicked.connect(self.commandButtonPressed)
        miscButtonGrid.addWidget(btn, 0, 0)
        btn = QtGui.QPushButton(self.commandButtons[Command.PREV_ACTION], self._widget)
        btn.clicked.connect(self.commandButtonPressed)
        miscButtonGrid.addWidget(btn, 0, 1)
        btn = QtGui.QPushButton(self.commandButtons[Command.NEXT_ACTION], self._widget)
        btn.clicked.connect(self.commandButtonPressed)
        miscButtonGrid.addWidget(btn, 0, 2)
        allWidgetsBox.addLayout(miscButtonGrid, 4, 0)
        
        
        # Fix layout and add main widget to the user interface
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('plastique'))
        vAllBox = QtGui.QVBoxLayout()
        vAllBox.addLayout(allWidgetsBox)
        vAllBox.addStretch(1)
        hAllBox = QtGui.QHBoxLayout()
        hAllBox.addLayout(vAllBox)   
        hAllBox.addStretch(1)
        self._widget.setObjectName('PbDGUI')
        self._widget.setLayout(hAllBox)
        context.add_widget(self._widget)

    def shutdown_plugin(self):
        # TODO unregister all publishers here
        self.commandOutput.unregister()
        pass

    def save_settings(self, plugin_settings, instance_settings):
        # TODO save intrinsic configuration, usually using:
        # instance_settings.set_value(k, v)
        pass

    def restore_settings(self, plugin_settings, instance_settings):
        # TODO restore intrinsic configuration, usually using:
        # v = instance_settings.value(k)
        pass

    #def trigger_configuration(self):
        # Comment in to signal that the plugin has a way to configure it
        # Usually used to open a dialog to offer the user a set of configuration

    def nActions(self):
        return len(self.actionIcons.keys())

    def createNewAction(self):
        nColumns = 6
        actionIndex = self.nActions()
        for key in self.actionIcons.keys():
             self.actionIcons[key].selected = False
             self.actionIcons[key].updateView()
        actIcon = ActionIcon(self._widget, actionIndex, self.actionPressed)
        self.actionGrid.addLayout(actIcon, int(actionIndex/nColumns), actionIndex%nColumns)
        self.actionIcons[actionIndex] = actIcon
        self.actionSteps[actionIndex] = []
        self.currentAction = actionIndex
        self.stepsBox.setTitle('Steps for Action ' + str(self.currentAction+1))

    def stepPressed(self, stepIndex):
        print 'pressed step ', stepIndex
        
    def actionPressed(self, actionIndex):
        for i in range(len(self.actionIcons.keys())):
            key = self.actionIcons.keys()[i]
            if key == actionIndex:
                 self.actionIcons[key].selected = True
                 self.actionIcons[key].updateView()
            else:
                 self.actionIcons[key].selected = False
                 self.actionIcons[key].updateView()
        self.currentAction = actionIndex
        self.stepsBox.setTitle('Steps for Action ' + str(self.currentAction+1))
        self.commandOutput.publish(Command('SWITCH_TO_ACTION' + str(actionIndex+1)))
        print 'pressed Action ', str(actionIndex+1)
        
    def commandButtonPressed(self):
        clickedButtonName = self._widget.sender().text()
        for key in self.commandButtons.keys():
            if (self.commandButtons[key] == clickedButtonName):
                qWarning('Sending speech command: '+ key)
                command = Command()
                command.command = key
                self.commandOutput.publish(command)
        
    def robotSoundReceived(self, soundReq):
        if (soundReq.command == SoundRequest.SAY):
            qWarning('Robot said: ' + soundReq.arg)
            self.speechLabel.setText('Robot said: ' + soundReq.arg)
    
    def respondToCommand(self, command):
        qWarning('Received signal:' + command.command)
        nActions = len(self.actionIcons.keys())
        if command.command == Command.CREATE_NEW_ACTION:
            self.createNewAction()
        
        elif command.command == Command.NEXT_ACTION:
            if (self.nActions() > 0):
                if (self.currentAction < nActions-1):
                    self.actionPressed(self.currentAction+1)
                else:
                    qWarning('No actions after Action ' + str(self.currentAction+1))
            else:
                qWarning('No actions created yet.')

        elif command.command == Command.PREV_ACTION:
            if (self.nActions() > 0):
                if (self.currentAction > 0):
                    self.actionPressed(self.currentAction-1)
                else:
                    qWarning('No actions before Action ' + str(self.currentAction+1))
            else:
                qWarning('No actions created yet.')
                
        elif command.command == Command.SAVE_POSE:
            if (self.nActions() > 0):
                self.savePose()
            else:
                qWarning('No actions created yet.')
            
    def savePose(self):
        nColumns = 10
        stepIndex = len(self.actionSteps[self.currentAction])
        stepIcon = StepIcon(self._widget, stepIndex, self.stepPressed)
        self.stepsGrid.addLayout(stepIcon, int(stepIndex/nColumns), stepIndex%nColumns)
        self.actionSteps[self.currentAction].append(stepIcon)
    
    def speechCommandReceived(self, command):
        qWarning('Received speech command:' + command.command)
        self.newCommand.emit(command)
        
    def robotSpeechReceived(self, speech):
        qWarning('Robot said: ' + speech.text)
        self.speechLabel.setText('Robot said: ' + speech.text)
        
    def robotStateReceived(self, speech):
        qWarning('Robot state: ' + speech.data)
        self.stateLabel.setText(speech.data)

    def getCommandList(self):
        path = os.popen('rospack find speech_recognition').read()
        path = path[0:len(path)-1]
        msgFile = open(path + '/msg/Command.msg', 'r')
        msgLine = msgFile.readline()
        self.commandList = []
        while (msgLine != ''):
            if (msgLine.find('=') != -1):
                lineParts = msgLine.split("=")
                commandStr = lineParts[len(lineParts)-1]
                while(commandStr[0] == ' '):
                    commandStr = commandStr[1:(len(commandStr))]
                while(commandStr[len(commandStr)-1] == ' ' or commandStr[len(commandStr)-1] == '\n'):
                    commandStr = commandStr[0:(len(commandStr)-1)]
                #commandStr = commandStr[1:(len(commandStr)-1)]
                if(commandStr != 'unrecognized'):
                    self.commandList.append(commandStr);
            msgLine = msgFile.readline()
        msgFile.close()
        
        
        