import os
import os.path
from pathlib import PurePosixPath
import glob
import json
import socket
from urllib.parse import urlparse, urljoin, unquote
from urllib3 import exceptions as urlexc

from PyQt6 import QtCore, QtWidgets
from .generated.fwmanager import Ui_FirmwareManagementDialog
from .. import constants
from ..fwutils import discoverFirmwares
from ..graphics import getIcon

import requests


REGURL = urljoin(constants.ARC_FW_BASEURL, 'registry.json')


class DownloadFirmware(QtCore.QThread):

    finished = QtCore.pyqtSignal(str)
    progressUpdate = QtCore.pyqtSignal(int)

    def __init__(self, url, target, parent=None):
        super().__init__(parent=parent)
        self.url = url
        self.target = target
        self.currentProgress = 0
        self.running = False

    def _exit(self, msg):
        self.running = False
        self.finished.emit(msg)

    def stop(self):
        self.running = False

    def run(self):

        self.running = True
        try:
            resp = requests.get(self.url, stream=True)
        except socket.gaierror:
            msg = 'Name or service not known'
            self._exit(msg)
            return
        except (requests.exceptions.ConnectionError, \
            urlexc.NewConnectionError, urlexc.MaxRetryError):
            msg = 'Could not establish a connection to server'
            self._exit(msg)
            return
        except requests.exceptions.Timeout:
            msg = 'Connection timed out'
            self._exit(msg)
            return
        except Exception as exc:
            msg = 'Unknown error while querying server: %s' % exc
            self._exit(msg)
            return

        if resp.status_code != 200:
            msg = 'Invalid server response: %d' % resp.status_code
            self._exit(msg)
            return

        size = int(resp.headers['Content-Length'])
        read = 0

        cancelled = False
        with open(self.target, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=1024*64):
                read += len(chunk)
                f.write(chunk)
                self.currentProgress = int(read/size * 100)
                self.progressUpdate.emit(self.currentProgress)

                if not self.running:
                    cancelled = True
                    break

        if cancelled:
            os.remove(self.target)
            self._exit('abort')
            return

        try:
            resp = requests.get('%s.txt' % self.url)
        except socket.gaierror:
            msg = 'Name or service not known'
            self._exit(msg)
            return
        except (requests.exceptions.ConnectionError, \
            urlexc.NewConnectionError, urlexc.MaxRetryError):
            msg = 'Could not establish a connection to server'
            self._exit(msg)
            return
        except requests.exceptions.Timeout:
            msg = 'Connection timed out'
            self._exit(msg)
            return
        except Exception as exc:
            msg = 'Unknown error while querying server: %s' % exc
            self._exit(msg)
            return

        if resp.status_code != 200:
            msg = 'Invalid server response: %d' % resp.status_code
            self._exit(msg)
            return

        with open('%s.txt' % self.target, 'wb') as f:
            f.write(resp.content)

        self._exit('')


class DownloadFirmwareInfo(QtCore.QThread):

    finished = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.data = None

    def stop(self):
        pass

    def run(self):

        msg = None

        try:
            resp = requests.get(REGURL, timeout=5)
            if resp.status_code != 200:
                msg = 'Invalid server response: %d' % resp.status_code
                self.data = None
            else:
                self.data = json.loads(resp.content)
        except socket.gaierror:
            msg = 'Name or service not known'
            self.data = None
        except (requests.exceptions.ConnectionError, \
            urlexc.NewConnectionError, urlexc.MaxRetryError):
            msg = 'Could not establish a connection to server'
            self.data = None
        except requests.exceptions.Timeout:
            msg = 'Connection timed out'
            self.data = None
        except Exception as exc:
            msg = 'Unknown error while querying server: %s' % exc
            self.data = None

        self.finished.emit(msg)


class FirmwareManagementDialog(Ui_FirmwareManagementDialog, QtWidgets.QDialog):

    def __init__(self, parent=None):
        Ui_FirmwareManagementDialog.__init__(self)
        QtWidgets.QDialog.__init__(self, parent=parent)

        self.operation = None
        self.messageTimer = QtCore.QTimer()
        self.messageTimer.timeout.connect(self.clearStatus)
        self.messageTimer.setSingleShot(True)

        self.setupUi(self)
        self.__setupIcons()
        self.__setupLocalTable()
        self.__setupRemoteTable()
        self.__populateLocalFirmwares()

        self.refreshFirmwareButton.clicked.connect(self.onRefreshClicked)
        self.downloadFirmwareButton.clicked.connect(self.onDownloadClicked)
        self.removeFirmwareButton.clicked.connect(self.onRemoveClicked)
        self.cancelOperationButton.clicked.connect(self.onStopClicked)

    def __setupIcons(self):
        self.downloadFirmwareButton.setIcon(getIcon('action-download'))
        self.removeFirmwareButton.setIcon(getIcon('action-delete'))
        self.refreshFirmwareButton.setIcon(getIcon('action-refresh'))
        self.cancelOperationButton.setIcon(getIcon('action-cancel'))

    def __setupLocalTable(self):
        table = self.localFirmwareTableWidget
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['Name', 'Verified'])
        table.verticalHeader().setVisible(False)
        hheader = table.horizontalHeader()
        hheader.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hheader.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        vheader = table.verticalHeader()
        vheader.setDefaultSectionSize(12)

    def __setupRemoteTable(self):
        table = self.remoteFirmwareTableWidget
        table.setColumnCount(1)
        table.setHorizontalHeaderLabels(['Available'])
        table.verticalHeader().setVisible(False)
        hheader = table.horizontalHeader()
        hheader.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        vheader = table.verticalHeader()
        vheader.setDefaultSectionSize(12)

    def __populateLocalFirmwares(self):

        # clear all items first
        while self.localFirmwareTableWidget.rowCount() > 0:
            self.localFirmwareTableWidget.removeRow(0)

        paths = QtCore.QStandardPaths.standardLocations(\
            QtCore.QStandardPaths.StandardLocation.AppDataLocation)

        for p in paths:
            actual_path = os.path.join(p, 'firmware')
            self.firmwarePathComboBox.addItem(actual_path, actual_path)

        allfws = discoverFirmwares(True)

        for (i, (k, v)) in enumerate(allfws.items()):
            nameItem = QtWidgets.QTableWidgetItem(k)
            installedItem = QtWidgets.QTableWidgetItem('Yes')
            verifiedItem = QtWidgets.QTableWidgetItem(str(v['verified']))
            nameItem.setData(QtCore.Qt.ItemDataRole.UserRole, v['path'])
            self.localFirmwareTableWidget.insertRow(\
                self.localFirmwareTableWidget.rowCount())
            self.localFirmwareTableWidget.setItem(i, 0, nameItem)
            self.localFirmwareTableWidget.setItem(i, 1, verifiedItem)

    def lockUnlockUi(self):
        wdgs = [\
            self.removeFirmwareButton,
            self.downloadFirmwareButton,
            self.refreshFirmwareButton,
            self.firmwarePathComboBox,
        ]

        for w in wdgs:
            w.setEnabled(self.operation is None)

        self.cancelOperationButton.setEnabled(self.operation is not None)

    def setStatus(self, text, kls=None):
        self.statusLabel.setText(text)
        if kls == 'error':
            self.statusLabel.setStyleSheet('color: red;')
        self.messageTimer.start(3000)

    def clearStatus(self):
        self.statusLabel.setText('')
        self.statusLabel.setStyleSheet('')

    def onRefreshClicked(self):

        def onFinished(msg):

            self.operation.wait()
            data = self.operation.data

            # clear previous contents
            while self.remoteFirmwareTableWidget.rowCount() > 0:
                self.remoteFirmwareTableWidget.removeRow(0)

            if data is None:
                self.setStatus('Failed to download firmware list: %s' % msg, 'error')
                return

            for (i, entry) in enumerate(reversed(sorted(data, key=lambda x: x['firmware']))):
                item = QtWidgets.QTableWidgetItem(entry['firmware'])
                item.setData(QtCore.Qt.ItemDataRole.UserRole, \
                    urljoin(constants.ARC_FW_BASEURL, entry['firmware']))
                self.remoteFirmwareTableWidget.insertRow(\
                    self.remoteFirmwareTableWidget.rowCount())
                self.remoteFirmwareTableWidget.setItem(i, 0, item)

            self.operation = None
            self.lockUnlockUi()
            self.setStatus('Firmware list downloaded')

        self.setStatus('Downloading firmware list…')
        self.operation = DownloadFirmwareInfo()
        self.lockUnlockUi()
        self.operation.finished.connect(onFinished)
        self.operation.start()

    def onDownloadClicked(self):

        def onFinished(msg):

            if self.operation is not None:
                self.operation.wait()
            if msg == '':
                # refresh local firmware list
                self.__populateLocalFirmwares()
                self.operation = None
                self.setStatus('Firmware downloaded')
            elif msg == 'abort':
                self.operation = None
                self.setStatus('Firmware download cancelled')
            else:
                self.operation = None
                self.setStatus('Firmware download failed: %s' % msg)
            self.lockUnlockUi()

        def onProgress(val):
            self.progressBar.setValue(val)

        targetdir = self.firmwarePathComboBox.currentData()
        if not os.path.exists(targetdir):
            try:
                os.makedirs(targetdir, mode=0o755, exist_ok=True)
            except PermissionError:
                self.setStatus('Download failed; target directory could not be created', \
                    'error')
                return

        if not os.access(targetdir, os.W_OK):
            self.setStatus('Download failed; target directory is not writable', \
                'error')
            return

        try:
            item = self.remoteFirmwareTableWidget.selectedItems()[0]
            url = item.data(QtCore.Qt.ItemDataRole.UserRole)
            # this MUST BE PurePosixPath otherwise it will not work on Windows
            fname = PurePosixPath(unquote(urlparse(url).path)).name
            target = os.path.join(targetdir, fname)
        except IndexError:
            # nothing selected
            return

        # at this point url and target file should be defined

        if os.path.exists(target):
            self.setStatus('Target already exists; delete it first', 'error')
            return

        self.setStatus('Downloading firmware…')
        self.operation = DownloadFirmware(url, target)
        self.operation.finished.connect(onFinished)
        self.operation.progressUpdate.connect(onProgress)
        self.progressBar.setValue(0)
        self.lockUnlockUi()
        self.operation.start()

    def onRemoveClicked(self):

        try:
            item = self.localFirmwareTableWidget.selectedItems()[0]
            row = item.row()
            fname = item.data(QtCore.Qt.ItemDataRole.UserRole)
            sigfname = '%s.txt' % fname
        except IndexError:
            return

        try:
            os.remove(fname)
            # delete the signature too, if there
            if os.path.exists(sigfname):
                os.remove(sigfname)

            self.localFirmwareTableWidget.removeRow(row)
        except PermissionError:
            self.setStatus('Insufficient permissions to delete %s' % \
                os.path.basename(fname), 'error')
        except Exception as exc:
            self.setStatus('Could not delete %s: %s' % \
                (os.path.basename(fname) % exc), 'error')

    def onStopClicked(self):
        if self.operation is not None:
            self.operation.stop()

    def accept(self, *args):
        if self.operation is not None:
            self.operation.stop()
        QtWidgets.QDialog.accept(self, *args)

    def reject(self, *args):
        if self.operation is not None:
            self.operation.stop()
        QtWidgets.QDialog.reject(self, *args)
