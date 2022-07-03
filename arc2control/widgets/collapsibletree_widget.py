from PyQt6 import QtWidgets


SECTION_ENABLED_STYLE = \
    """QPushButton { text-align: left; padding: 5px; font-weight: bold; }"""
SECTION_DISABLED_STYLE = """QPushButton { text-align: left; padding: 5px; }"""


class SectionExpandButton(QtWidgets.QPushButton):

    def __init__(self, item, text="", expanded=True, parent=None):
        super().__init__('', parent)
        self.section = item
        self.section.setExpanded(expanded)
        self.innerText = text
        self.setText(self.innerText)
        self.clicked.connect(self.onClicked)
        self.setStyleSheet(SECTION_ENABLED_STYLE)

    def onClicked(self):
        if self.section.isExpanded():
            self.section.setExpanded(False)
            self.setStyleSheet(SECTION_DISABLED_STYLE)
        else:
            self.section.setExpanded(True)
            self.setStyleSheet(SECTION_ENABLED_STYLE)

        self.__resetText()

    def setText(self, txt):
        if self.section.isExpanded():
            super().setText('+ ' + txt)
        else:
            super().setText('– ' + txt)

    def __resetText(self):
        self.setText(self.innerText)


class CollapsibleTreeWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # all widgets managed by this tree
        self.widgets = []

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setObjectName('holderTree')
        self.tree.setStyleSheet(\
            'QTreeWidget#holderTree::item:hover { background-color: transparent; }')
        self.tree.setHeaderHidden(True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)
        self.tree.setIndentation(0)

    def __baseColorHex(self):
        color = self.tree.palette().base().color()
        return "#%2x%2x%2x" % (color.red(), color.green(), color.blue())

    def addWidget(self, title, wdg, expanded=True):

        self.widgets.append(wdg)

        buttonTreeItem = QtWidgets.QTreeWidgetItem()
        self.tree.addTopLevelItem(buttonTreeItem)
        button = SectionExpandButton(buttonTreeItem, text=title, expanded=expanded)
        self.tree.setItemWidget(buttonTreeItem, 0, button)

        section = QtWidgets.QTreeWidgetItem(buttonTreeItem)
        section.setDisabled(True)
        frame = QtWidgets.QFrame()
        frame.setObjectName('holderFrame')
        frame.setStyleSheet('QFrame#holderFrame:hover { background-color: %s; }' % \
            self.__baseColorHex())
        flayout = QtWidgets.QVBoxLayout(frame)
        flayout.addWidget(wdg)
        self.tree.setItemWidget(section, 0, frame)
        buttonTreeItem.addChild(section)

        return wdg
