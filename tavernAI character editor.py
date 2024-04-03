from PIL import Image
from PIL.PngImagePlugin import PngImageFile, PngInfo
import base64
import json

base = {
    'spec': 'chara_card_v2',
    'spec_version': '2.0',
    'data': {
        'name': '',
        'description': "",
        'personality': '',
        'scenario': "",
        'first_mes': '',
        'mes_example': '',
        'creator_notes': '',
        'system_prompt': '',
        'post_history_instructions': '',
        'alternate_greetings': [],
        'tags': [],
        'creator': '',
        'character_version': '',
        'extensions': {}
    }
}

TEMP_ROOT = "."

def read_character(path):
    image = PngImageFile(path)
    user_comment = image.text.get('chara', None)
    if user_comment == None:
        return json.loads(json.dumps(base)) # deep copy of an empty character dictionary
    base64_bytes = user_comment.encode('utf-8')  # Convert the base64 string to bytes
    json_bytes = base64.b64decode(base64_bytes)  # Decode the base64 bytes to JSON bytes
    json_str = json_bytes.decode('utf-8')  # Convert the JSON bytes to a string
    data = json.loads(json_str)  # Convert the string to JSON data

    if data.get('spec') != 'chara_card_v2':
        newData = json.loads(json.dumps(base)) # deep copy of an empty character dictionary
        newData["data"] = data
        data = newData
    return data

def write_character(path, data):
    json_str = json.dumps(data)
    base64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    image = Image.open(path)
    metadata = PngInfo()
    metadata.add_text('chara', base64_str)
    image.save(path, 'PNG', pnginfo=metadata)

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QLabel, QListWidgetItem, QStackedWidget, QSplitter
from PyQt5.QtWidgets import QLineEdit, QPlainTextEdit, QListWidget, QPushButton, QFormLayout, QTabWidget, QHBoxLayout, QFileDialog
import os
import traceback

def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("caught:", tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

class AlternateGreetingWidget(QWidget):
    def __init__(self, parent=None):
        super(AlternateGreetingWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)
        self.editor = QPlainTextEdit(self)
        self.delete_button = QPushButton("Delete", self)
        self.layout.addWidget(self.editor)
        self.layout.addWidget(self.delete_button)


class EditorWidget(QWidget):
    def __init__(self, fullData, filePath):
        super().__init__()
        
        self.fullData = fullData
        self.filePath = filePath
        
        self.tab_widget = QTabWidget()

        # Create the tabs
        self.tabCommon = QWidget()
        self.tabUncommon = QWidget()
        self.tabCharacterBook = QWidget()

        # Add tabs
        self.tab_widget.addTab(self.tabCommon, "Common Fields")
        self.tab_widget.addTab(self.tabUncommon, "Uncommon Fields")
        self.tab_widget.addTab(self.tabCharacterBook, "Character Book")

        # Create first tab layout
        self.tabCommon_layout = QFormLayout(self.tabCommon)
        self.nameEdit = QLineEdit()
        self.nameEdit.setToolTip("""Keep it short! The user will probably have to type it a lot.""")
        self.tabCommon_layout.addRow("Name:", self.nameEdit)
        self.descriptionEdit = QPlainTextEdit()
        self.descriptionEdit.setToolTip(
            """Will be included in every prompt. A detailed description of the most important information the model
needs to know about the character. A thorough description is somewhere in the range of 300-800 tokens,
and probably should not exceed 1000 tokens.""")
        self.tabCommon_layout.addRow("Description:", self.descriptionEdit)
        self.personalityEdit = QPlainTextEdit()
        self.personalityEdit.setToolTip("""A very brief summary of the character's personality.""")
        self.tabCommon_layout.addRow("Personality:", self.personalityEdit)
        self.scenarioEdit = QPlainTextEdit()
        self.scenarioEdit.setToolTip("""A very brief summary of the current circumstances to the conversation.""")
        self.tabCommon_layout.addRow("Scenario:", self.scenarioEdit)
        self.firstMesEdit = QPlainTextEdit()
        self.firstMesEdit.setToolTip(
            """A good first message can make a huge difference in the length and quality of the bot's responses.
write this greeting as if the bot had written it. Avoid describing the user's actions and dialogue too
much or the bot might act and speak for the user in subsequent responses.""")
        self.tabCommon_layout.addRow("First Message:", self.firstMesEdit)
        self.mesExampleEdit = QPlainTextEdit()
        self.mesExampleEdit.setToolTip("""<START>
{{user}}: "How do example messages work?"
{{char}}: *He does something interesting, then another interesting thing.* "Oh, hello! These example
messages are very important. But I can't tell you why!" *{{char}} does more interesting things, because
this example message will influence the style, length, and quality of the bot's responses until the
context fills up.*
<START>
{{user}}: "Are the example messages sent with every prompt?"
{{char}}: "Not every prompt, just until the context fills up with your actual conversation." *{{char}}
thinks about how just two or three good example conversations like this placeholder text, and formatted
the same way, can drastically improve the quality of your bot.*""")
        self.tabCommon_layout.addRow("Message Example:", self.mesExampleEdit)

        # Create second tab layout
        self.tabUncommon_layout = QFormLayout(self.tabUncommon)        
        self.alternateGreetingsList = QListWidget()        
        self.alternateGreetingsList.setToolTip(
            """This list can contain any number of alternative first messages for this character.
Frontends should offer the ability for the user to select which first message to use when starting a
new conversation.""")
        self.tabUncommon_layout.addRow("Alternate Greetings:", self.alternateGreetingsList)
        self.addAlternateGreetingButton = QPushButton("Add Alternate Greeting")
        self.addAlternateGreetingButton.clicked.connect(self.add_alternate_greeting)
        self.tabUncommon_layout.addRow(self.addAlternateGreetingButton)

        self.systemPromptEdit = QPlainTextEdit()
        self.systemPromptEdit.setToolTip(
            """Frontends replace what users understand to be the "system prompt" global setting with the
value inside this field. The {{original}} placeholder can be used in this text, which is replaced with
the system prompt string that the frontend would have used in the absence of a character system_prompt
(e.g. the user's own system prompt).""")
        self.tabUncommon_layout.addRow("System Prompt:", self.systemPromptEdit)
        self.postHistoryInstructionsEdit = QPlainTextEdit()
        self.postHistoryInstructionsEdit.setToolTip(
            """Frontends replace what users understand to be the "ujb/jailbreak" setting with the value inside
this field. The {{original}} placeholder can be used in this text, which is replaced with the
"ujb/jailbreak" string that the frontend would have used in the absence of a character system_prompt
(e.g. the user's own ujb/jailbreak).""")
        self.tabUncommon_layout.addRow("Post History Instructions:", self.postHistoryInstructionsEdit)
        self.tagsList = QLineEdit()
        self.tagsList.setToolTip("""comma, separated, list, of, tags. Used for discoverability, isn't used by the chatbot.""")
        self.tabUncommon_layout.addRow("Tags:", self.tagsList)
        self.characterVersionEdit = QLineEdit()
        self.characterVersionEdit.setToolTip("""A version string for tracking updates to this character.""")
        self.tabUncommon_layout.addRow("Character Version:", self.characterVersionEdit)
        self.creatorEdit = QLineEdit()
        self.creatorEdit.setToolTip("""The name of the person who created this character.""")
        self.tabUncommon_layout.addRow("Creator:", self.creatorEdit)
        self.creatorNotesEdit = QPlainTextEdit()
        self.creatorNotesEdit.setToolTip(
            """The text in this field is used for 'discoverability.' The first line might be a very simple
description of the bot - 'A friendly clown with a knife, in a dark alley'. Expect most users to only
see that first line. The rest of this value can be used for important notes the user may find helpful
to get the best experience from the bot.""")
        self.tabUncommon_layout.addRow("Creator Notes:", self.creatorNotesEdit)

        # Create third tab layout
        self.tabCharacterBook_layout = QFormLayout(self.tabCharacterBook)

        #TODO
        
        self.updateUIFromData()

        # Create the buttons
        self.saveButton = QPushButton("&Save")
        self.saveButton.setToolTip("""Updates the character data stored in the character card PNG.""")
        self.saveButton.root = self
        self.saveButton.clicked.connect(self.saveClicked)
        self.exportButton = QPushButton('&Export JSON')
        self.exportButton.setToolTip("""Saves the data for this character as a separate JSON file. Doesn't update the character card PNG.""")
        self.exportButton.root = self
        self.exportButton.clicked.connect(self.exportClicked)
        self.importButton = QPushButton('&Import JSON')
        self.importButton.setToolTip("""Loads character data from a JSON file, overwriting the data currently displayed in the editor.
Doesn't update the character card PNG, you'll need to click "Save" after importing to do that.""")
        self.importButton.root = self
        self.importButton.clicked.connect(self.importClicked)

        # Create a horizontal layout for the buttons
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.saveButton)
        self.button_layout.addWidget(self.exportButton)
        self.button_layout.addWidget(self.importButton)

        # Create a vertical layout for the root widget
        self.root_layout = QVBoxLayout(self)
        self.root_layout.addWidget(self.tab_widget)
        self.root_layout.addLayout(self.button_layout)

        # Set QVBoxLayout as the layout
        self.setLayout(self.root_layout)

    def updateUIFromData(self):
        data = self.fullData["data"]
        self.nameEdit.setText(data.get("name"))
        self.descriptionEdit.setPlainText(data.get("description"))
        self.personalityEdit.setPlainText(data.get("personality"))
        self.scenarioEdit.setPlainText(data.get("scenario"))
        self.firstMesEdit.setPlainText(data.get("first_mes"))
        self.mesExampleEdit.setPlainText(data.get("mes_example"))

        #initialize alternate greetings
        self.alternateGreetingsList.clear()
        for greeting in data.get("alternate_greetings", []):
            self.add_alternate_greeting(greeting)

        self.systemPromptEdit.setPlainText(data.get("system_prompt"))
        self.postHistoryInstructionsEdit.setPlainText(data.get("post_history_instructions"))
        self.tagsList.setText(", ".join(data.get("tags", [])))
        self.characterVersionEdit.setText(data.get("character_version"))
        self.creatorEdit.setText(data.get("creator"))
        self.creatorNotesEdit.setPlainText(data.get("creator_notes"))

    def updateDataFromUI(self):
        fullData = self.fullData
        data = fullData["data"]

        data["name"] = str(self.nameEdit.text())
        data["tags"] = [x.strip() for x in str(self.tagsList.text()).split(',')]
        data["character_version"] = str(self.characterVersionEdit.text())
        data["description"] = str(self.descriptionEdit.toPlainText())
        data["personality"] = str(self.personalityEdit.toPlainText())
        data["scenario"] = str(self.scenarioEdit.toPlainText())
        data["first_mes"] = str(self.firstMesEdit.toPlainText())
        data["mes_example"] = str(self.mesExampleEdit.toPlainText())

        alternateGreetings = []
        for i in range(self.alternateGreetingsList.count()):
            item = self.alternateGreetingsList.item(i)
            greeting = self.alternateGreetingsList.itemWidget(item)
            alternateGreetings.append(greeting.editor.toPlainText())
        data["alternate_greetings"] = alternateGreetings
        data["system_prompt"] = str(self.systemPromptEdit.toPlainText())
        data["post_history_instructions"] = str(self.postHistoryInstructionsEdit.toPlainText())
        data["creator"] = str(self.creatorEdit.text())
        data["creator_notes"] = str(self.creatorNotesEdit.toPlainText())

    def saveClicked(self):
        self.updateDataFromUI()
        write_character(self.filePath, self.fullData)

    def exportClicked(self):
        self.updateDataFromUI()
        jsonFilepath = self.filePath[:-3]+"json"
        with open(jsonFilepath, "w", encoding="utf-8") as f:
            json.dump(self.fullData, f)

    def importClicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "/path/to/default/folder", "JSON Files (*.json)", options=options)
        if fileName:
            with open(fileName, "r", encoding="utf-8") as f:
                self.fullData = json.load(f)
        self.updateUIFromData()

    def add_alternate_greeting(self, text=None):
        widget_item = QListWidgetItem(self.alternateGreetingsList)
        custom_widget = AlternateGreetingWidget(self.alternateGreetingsList)
        if text:
            custom_widget.editor.setPlainText(text)
        widget_item.setSizeHint(custom_widget.sizeHint())
        self.alternateGreetingsList.addItem(widget_item)
        self.alternateGreetingsList.setItemWidget(widget_item, custom_widget)
        custom_widget.delete_button.clicked.connect(lambda: self.delete_alternate_greeting(widget_item))

    def delete_alternate_greeting(self, item):
        row = self.alternateGreetingsList.row(item)
        self.alternateGreetingsList.takeItem(row)


from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QSize, pyqtSignal

class AspectRatioLabel(QLabel):
    def __init__(self, pixmap):
        super().__init__()
        self._pixmap = QPixmap(pixmap)

    def paintEvent(self, event):
        size = self.size()
        painter = QPainter(self)
        painter.setBrush(QColor(Qt.white))
        painter.drawRect(0, 0, size.width(), size.height())
        scaledPix = self._pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # Calculate the starting point (top left of the image)
        startPointX = int((size.width() - scaledPix.width()) / 2)
        startPointY = int((size.height() - scaledPix.height()) / 2)
        painter.drawPixmap(startPointX, startPointY, scaledPix)

class ImageThumbnail(QWidget):
    def __init__(self, imagePath):
        super().__init__()
        layout = QHBoxLayout()
        self.setLayout(layout)
        imageLabel = AspectRatioLabel(imagePath)
        imageLabel.setFixedSize(QSize(64, 64))
        layout.addWidget(imageLabel)
        textLabel = QLabel(os.path.basename(imagePath)[:-4])
        layout.addWidget(textLabel)

class ImageList(QListWidget):
    directoryChanged = pyqtSignal()
    
    def __init__(self, dirPath):
        super().__init__()
        self.dirPath = dirPath
        self.itemClicked.connect(self.showImage)
        self.stack = QStackedWidget()
        self.loadImages()

    def loadImages(self):
        self.clear()
        self.stack = QStackedWidget()
        for file in os.listdir(self.dirPath):
            if file.endswith(".png"):
                item = QListWidgetItem(self)
                self.addItem(item)
                imagePath = os.path.join(self.dirPath, file)
                imageLabel = ImageThumbnail(imagePath)
                data = read_character(imagePath)
                item.setSizeHint(imageLabel.sizeHint())
                self.setItemWidget(item, imageLabel)
                self.stack.addWidget(EditorWidget(data, imagePath))

    def showImage(self, item):
        index = self.row(item)
        self.stack.setCurrentIndex(index)
        self.stack.currentWidget().show()

    def changeDirectory(self):
        newDirpath = QFileDialog.getExistingDirectory(self, "Select Directory")
        if newDirpath != '':
            self.dirPath = newDirpath
            self.updateDirectory()

    def updateDirectory(self):
        self.loadImages()
        self.directoryChanged.emit()

class MainWindow(QWidget):
    def __init__(self, dirPath):
        super().__init__()
        self.setWindowTitle("TavernAI Character Editor")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)
        self.imageList = ImageList(dirPath)
        self.imageList.directoryChanged.connect(self.updateStack)
        self.changeDirButton = QPushButton("Change Directory", self)
        self.changeDirButton.clicked.connect(self.imageList.changeDirectory)
        self.refreshDirButton = QPushButton("Refresh", self)
        self.refreshDirButton.clicked.connect(self.imageList.updateDirectory)

        self.rightPanel = QWidget()
        self.rightPanelLayout = QVBoxLayout()
        self.rightPanel.setLayout(self.rightPanelLayout)
        self.rightPanelLayout.addWidget(self.changeDirButton)
        self.rightPanelLayout.addWidget(self.refreshDirButton)
        self.rightPanelLayout.addWidget(self.imageList)
        
        self.splitter.addWidget(self.imageList.stack)
        self.splitter.addWidget(self.rightPanel)

    def updateStack(self):
        self.splitter.widget(0).deleteLater()
        self.splitter.insertWidget(0, self.imageList.stack)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(TEMP_ROOT)  # Replace with your directory path
    window.show()
    sys.exit(app.exec_())

