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

PLAINTEXT_EDITOR_MAX_HEIGHT = 50

# Various global methods

# Extract JSON character data from an image. Handles both V1 and V2 TavernAI format, returns V2.
# Creates a new character data dict if the image doesn't have one.
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
    if not isinstance(data["data"].get("tags", []), list):
        data["data"]["tags"] = []
    if not isinstance(data["data"].get("alternate_greetings", []), list):
        data["data"]["alternate_greetings"] = []
    if "character_book" in data["data"] and "entries" in data["data"]["character_book"]:
        for entry in data["data"]["character_book"]["entries"]:
            if not isinstance(entry.get("secondary_keys"), list):
                entry["secondary_keys"] = []
    return data

#Writes character data back to the image
def write_character(path, data):
    json_str = json.dumps(data)
    base64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    image = Image.open(path)
    metadata = PngInfo()
    metadata.add_text('chara', base64_str)
    image.save(path, 'PNG', pnginfo=metadata)

#ensures that agnai, sillytavern, and tavernai characterbooks all come out in the same
#format, ready for insertion into a tavernai character
def process_worldbook(data):
    if not isinstance(data, dict):
        print(type(data))
        return None
    if not "entries" in data:
        print("not entries")
        if "spec" in data and data["spec"] =='chara_card_v2' and "data" in data and "character_book" in data["data"]:
            return data["data"]["character_book"]        
        return None
    if isinstance(data["entries"], dict):
        entries = list(data["entries"].values())
        data["entries"] = entries
    for entry in data["entries"]:
        if "entry" in entry and entry.get("content") == entry.get("entry"):
            del entry["entry"]
            #The agnai worldbooks I've looked at have duplicte contents, I'm making an executive decision here
            #to pare that down since the spec for tavernai characters would ignore this data anyway
    return data

#merges worldBook into characterBook
def import_worldbook(characterBook, worldBook):
    desc = worldBook.get("description", "")
    if desc != "" and characterBook.get("description", "") == "":
        characterBook["description"] = desc
    name = worldBook.get("name", "")
    if name != "" and characterBook.get("name", "") == "":
        characterBook["name"] = name
    characterBook["entries"] = characterBook.get("entries", [])
    characterBook["entries"] += worldBook["entries"]
    worldExtensions = worldBook.get("extensions", {})
    characterExtensions = characterBook.get("extensions", {})
    characterBook["extensions"] = characterExtensions | worldExtensions
    return characterBook

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QLabel, QListWidgetItem, QStackedWidget, QSplitter
from PyQt5.QtWidgets import QLineEdit, QPlainTextEdit, QListWidget, QPushButton, QFormLayout, QTabWidget, QHBoxLayout, QFileDialog
from PyQt5.QtWidgets import QCheckBox, QSizePolicy, QComboBox, QGridLayout, QAbstractItemView
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt
import os
import traceback

def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("caught:", tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

#Common functionality for checkboxes that can be undefined
def convertBoolToTristate(data):
    if data == True:
        return Qt.Checked
    elif data == False:
        return Qt.Unchecked
    return Qt.PartiallyChecked
def convertTristateToBool(data):
    if data == Qt.Checked:
        return True
    elif data == Qt.Unchecked:
        return False
    return None

#Handle malformed extensions fields
def safeJSONLoads(jsonstring):
    try:
        return json.loads(jsonstring)
    except:
        return jsonstring

def safeNumberConversion(stringVal, default=None):
    try:
        return float(stringVal)
    except ValueError:
        return default

# For handling keys that are optional. If the value is equal to the nullvalue
# it gets removed from the dict entirely.
def updateOrDeleteKey(dictionary, key, value, nullvalue=None):
    if value != nullvalue:
        dictionary[key] = value
    elif key in dictionary:
        del dictionary[key]

# A simple text editor with a delete button, for use in the alternate greetings widget
class AlternateGreetingWidget(QWidget):
    def __init__(self, parent=None):
        super(AlternateGreetingWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)
        self.editor = QPlainTextEdit(self)
        self.delete_button = QPushButton("Delete", self)
        self.layout.addWidget(self.editor)
        self.layout.addWidget(self.delete_button)

#CharacterBook entry.
class EntryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        # Just the most basic properites, the keys and content for the entry
        self.simple_attributes = QWidget(self)
        self.simple_attributes_layout = QGridLayout(self.simple_attributes)
        self.layout.addWidget(self.simple_attributes)

        self.simple_attributes_layout.addWidget(QLabel("Keys", self.simple_attributes), 0, 0)
        self.keys_field = QLineEdit(self.simple_attributes)
        self.simple_attributes_layout.addWidget(self.keys_field, 0, 1)
        self.delete_button = QPushButton("Delete", self)
        self.simple_attributes_layout.addWidget(self.delete_button, 0, 2)
        self.simple_attributes_layout.addWidget(QLabel("Content", self.simple_attributes), 1, 0)
        self.content_field = QPlainTextEdit(self.simple_attributes)
        self.content_field.setMaximumHeight(PLAINTEXT_EDITOR_MAX_HEIGHT)
        self.content_field.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.simple_attributes_layout.addWidget(self.content_field, 1, 1, 1, 2)

        # All the rest of the properties are contained here so they can be shown and hidden together
        self.complex_attributes = QWidget(self)
        self.complex_attributes_layout = QGridLayout(self.complex_attributes)
        self.layout.addWidget(self.complex_attributes)

        grid = self.complex_attributes_layout

        grid.addWidget(QLabel("Name", self), 0, 0)
        self.name_edit = QLineEdit(self)
        self.name_edit.setToolTip("not used in prompt engineering")
        grid.addWidget(self.name_edit, 0, 1)

        self.booleans = QWidget(self)
        self.booleans_layout = QHBoxLayout(self.booleans)
        self.booleans.setLayout(self.booleans_layout)
        grid.addWidget(self.booleans, 1, 0, 1, 2)
        bools = self.booleans_layout
        self.enabled_checkbox = QCheckBox("Enabled", self) #not tristate, enabled is required by the spec
        self.enabled_checkbox.setToolTip("Whether this entry is to be actually used by the character.")
        bools.addWidget(self.enabled_checkbox)
        self.case_sensitive_checkbox = QCheckBox("Case Sensitive", self)
        self.case_sensitive_checkbox.setTristate(True)
        self.case_sensitive_checkbox.setToolTip("""Whether the keyword search should pay attention to upper/lower case.
This tristate checkbox allows you to set a value that may be true, false, or undefined. The specifications for character cards
indicate that this particular data parameter is optional and may be absent entirely, which is represented by the "undefined" state.""")
        bools.addWidget(self.case_sensitive_checkbox)
        self.constant_checkbox = QCheckBox("Constant", self)
        self.constant_checkbox.setTristate(True)
        self.constant_checkbox.setToolTip("""if true, always inserted in the prompt (within budget limit)
This tristate checkbox allows you to set a value that may be true, false, or undefined. The specifications for character cards
indicate that this particular data parameter is optional and may be absent entirely, which is represented by the "undefined" state.""")
        bools.addWidget(self.constant_checkbox)
        positionLabel = QLabel("Position")
        positionLabel.setAlignment(Qt.AlignRight)
        bools.addWidget(positionLabel)
        self.positionBox = QComboBox(self)
        self.positionBox.addItem("")  # Add an empty "unset" value
        self.positionBox.addItem("Before character") #before_char
        self.positionBox.addItem("After character") #after_char
        self.positionBox.setToolTip("whether the entry is placed before or after the character defs")
        bools.addWidget(self.positionBox)

        doubleValidator = QDoubleValidator()
        self.numbers = QWidget(self)
        self.numbers_layout = QHBoxLayout(self.numbers)
        self.numbers.setLayout(self.numbers_layout)
        grid.addWidget(self.numbers, 2, 0, 1, 2)
        nums = self.numbers_layout
        nums.addWidget(QLabel("Insertion Order", self))
        self.insertion_order_edit = QLineEdit(self)
        self.insertion_order_edit.setToolTip("if two entries inserted, a lower insertion order causes it to be inserted higher")
        self.insertion_order_edit.setValidator(doubleValidator)
        nums.addWidget(self.insertion_order_edit)
        nums.addWidget(QLabel("Priority", self))
        self.priority_edit = QLineEdit(self)
        self.priority_edit.setToolTip("if token budget reached, lower priority value entries are discarded first")
        self.priority_edit.setValidator(doubleValidator)
        nums.addWidget(self.priority_edit)
        nums.addWidget(QLabel("ID", self))
        self.id_edit = QLineEdit(self) 
        self.id_edit.setToolTip("not used in prompt engineering")
        self.id_edit.setValidator(doubleValidator)
        nums.addWidget(self.id_edit)
        
        grid.addWidget(QLabel("Comment", self), 3, 0)
        self.comment_edit = QPlainTextEdit(self)
        self.comment_edit.setMaximumHeight(PLAINTEXT_EDITOR_MAX_HEIGHT)
        self.comment_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.comment_edit.setToolTip("not used in prompt engineering")
        grid.addWidget(self.comment_edit, 3, 1)
        self.selective_checkbox = QCheckBox("Selective", self)
        self.selective_checkbox.setTristate(True)
        self.selective_checkbox.stateChanged.connect(self.setSelective)
        self.selective_checkbox.setToolTip("""if `true`, require a key from both `keys` and `secondary_keys` to trigger the entry.
This tristate checkbox allows you to set a value that may be true, false, or undefined. The specifications for character cards
indicate that this particular data parameter is optional and may be absent entirely, which is represented by the "undefined" state.""")
        grid.addWidget(self.selective_checkbox, 4, 0)
        #self.secondary_keys_label = QLabel("Secondary Keys", self) #don't need this label, using the selective checkbox as one
        self.secondary_keys_edit = QLineEdit(self)
        self.secondary_keys_edit.setToolTip("comma-separated secondary keys, only used if \"selective\" is set to true.")
        grid.addWidget(self.secondary_keys_edit, 4, 1)
        grid.addWidget(QLabel("Extensions", self), 5, 0)
        self.extensions_edit = QPlainTextEdit(self)
        self.extensions_edit.setMaximumHeight(PLAINTEXT_EDITOR_MAX_HEIGHT)
        self.extensions_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.extensions_edit.setToolTip("A block of JSON values used by non-standard chatbot extensions.")
        grid.addWidget(self.extensions_edit, 5, 1)

    # Enables/disables the secondary keys control
    def setSelective(self, state):
        self.secondary_keys_edit.setEnabled(state == Qt.Checked)

    # Takes an entry dict and updates the UI's contents to match
    def setData(self, entry):
        if not entry:
            self.enabled_checkbox.setChecked(True) #default new entries to enabled
            self.extensions_edit.setPlainText("{}")
            return
        self.content_field.setPlainText(entry.get("content"))
        self.keys_field.setText(", ".join(entry.get("keys", [])))
        self.name_edit.setText(entry.get("name"))
        self.enabled_checkbox.setChecked(entry.get("enabled", True)) #defaulting to true because that just seems like the most likely intent when this is absent entirely
        self.case_sensitive_checkbox.setCheckState(convertBoolToTristate(entry.get("case_sensitive", None)))
        self.constant_checkbox.setCheckState(convertBoolToTristate(entry.get("constant", None)))
        position = entry.get("position", "")
        if position == "before_char":
            position = "Before character"
        elif position == "after_char":
            position = "After character"
        else:
            position = ""
        self.positionBox.setCurrentText(position)
        self.insertion_order_edit.setText(str(entry.get("insertion_order", "0")))
        self.priority_edit.setText(str(entry.get("priority", "")))
        self.id_edit.setText(str(entry.get("id", "")))
        self.comment_edit.setPlainText(entry.get("comment"))
        self.selective_checkbox.setCheckState(convertBoolToTristate(entry.get("selective", None)))
        self.secondary_keys_edit.setText(", ".join(entry.get("secondary_keys", [])))
        self.secondary_keys_edit.setEnabled(entry.get("selective", False))
        self.extensions_edit.setPlainText(json.dumps(entry.get("extensions", {})))

    # Puts all of the data from the UI into a dict to hand back
    def getData(self):
        entry_dict = {}
        entry_dict["keys"] = [x.strip() for x in str(self.keys_field.text()).split(',')]
        entry_dict["content"] = self.content_field.toPlainText()
        entry_dict["extensions"] = safeJSONLoads(self.extensions_edit.toPlainText())
        entry_dict["enabled"] = self.enabled_checkbox.checkState() == Qt.Checked
        #According to the specs, insertion order is mandatory. Default it to 0.
        entry_dict["insertion_order"] = safeNumberConversion(self.insertion_order_edit.text(), 0)
        updateOrDeleteKey(entry_dict, "case_sensitive", convertTristateToBool(self.case_sensitive_checkbox.checkState()))
        updateOrDeleteKey(entry_dict, "name", self.name_edit.text(), "")
        updateOrDeleteKey(entry_dict, "priority", safeNumberConversion(self.priority_edit.text()))
        updateOrDeleteKey(entry_dict, "id", safeNumberConversion(self.id_edit.text()))
        updateOrDeleteKey(entry_dict, "comment", self.comment_edit.toPlainText(), "")
        updateOrDeleteKey(entry_dict, "selective", convertTristateToBool(self.selective_checkbox.checkState()))
        updateOrDeleteKey(entry_dict, "secondary_keys", [x.strip() for x in str(self.secondary_keys_edit.text()).split(',')])
        updateOrDeleteKey(entry_dict, "constant", convertTristateToBool(self.constant_checkbox.checkState()))
        position = self.positionBox.currentText()
        if position == "Before character":
            entry_dict["position"] = "before_char"
        elif position == "After character":
            entry_dict["position"] = "after_char"
        return entry_dict

# Much more complicated than the main window's list of properties, so it gets its own widget
class CharacterBookWidget(QWidget):
    def __init__(self, fullData, parent=None):
        super().__init__(parent)

        self.fullData = fullData
        self.layout = QVBoxLayout(self)

        # A checkbox for toggling view mode
        self.view_checkbox = QCheckBox("Simple View", self)
        self.view_checkbox.stateChanged.connect(self.toggle_view)
        self.layout.addWidget(self.view_checkbox)

        self.simple_attributes = QWidget(self)
        self.simple_attributes_layout = QFormLayout(self.simple_attributes)
        self.layout.addWidget(self.simple_attributes)
        
        # Add fields for top-level attributes
        self.name_field = QLineEdit(self)
        #self.name_field.setToolTip("")
        self.simple_attributes_layout.addRow("Name", self.name_field)
        self.description_field = QPlainTextEdit(self)
        self.description_field.setMaximumHeight(PLAINTEXT_EDITOR_MAX_HEIGHT)
        self.description_field.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        #self.description_field.setToolTip("")
        self.simple_attributes_layout.addRow("Description", self.description_field)

        self.complex_attributes = QWidget(self)
        self.complex_attributes_layout = QHBoxLayout(self.complex_attributes)
        self.layout.addWidget(self.complex_attributes)

        intValidator = QIntValidator()

        self.scan_depth_label = QLabel("Scan Depth", self)
        self.complex_attributes_layout.addWidget(self.scan_depth_label)
        self.scan_depth_editor = QLineEdit("", self)
        self.scan_depth_editor.setToolTip("Chat history depth scanned for keywords.")
        self.scan_depth_editor.setValidator(intValidator)
        self.complex_attributes_layout.addWidget(self.scan_depth_editor)
        self.token_budget_label = QLabel("Token Budget", self)
        self.complex_attributes_layout.addWidget(self.token_budget_label)
        self.token_budget_editor = QLineEdit("", self)
        self.token_budget_editor.setToolTip("Sets how much of the context can be taken up by entries.")
        self.token_budget_editor.setValidator(intValidator)
        self.complex_attributes_layout.addWidget(self.token_budget_editor)
        self.recursive_scanning = QCheckBox("Recursive Scanning", self)
        self.recursive_scanning.setToolTip("""whether entry content can trigger other entries.
This tristate checkbox allows you to set a value that may be true, false, or undefined. The specifications for character cards
indicate that this particular data parameter is optional and may be absent entirely, which is represented by the "undefined" state.""")
        self.recursive_scanning.setTristate(True) #can be None
        self.complex_attributes_layout.addWidget(self.recursive_scanning)

        self.extensions_form = QWidget(self)
        self.extensions_form_layout = QFormLayout(self.extensions_form)
        self.extensions_edit = QPlainTextEdit(self)
        self.extensions_edit.setMaximumHeight(PLAINTEXT_EDITOR_MAX_HEIGHT)
        self.extensions_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.extensions_edit.setToolTip("A block of JSON values used by non-standard chatbot extensions.")
        self.extensions_form_layout.addRow("Extensions", self.extensions_edit)
        self.layout.addWidget(self.extensions_form)
        
        # Add a list widget for the entries
        self.entries_list = QListWidget(self)
        self.entries_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.entries_list.setStyleSheet("QListWidget::item { border-bottom: 1px solid black; }")
        self.layout.addWidget(self.entries_list)

        self.buttonWidget = QWidget(self)
        self.buttonWidgetLayout = QHBoxLayout()
        self.buttonWidget.setLayout(self.buttonWidgetLayout)
        self.layout.addWidget(self.buttonWidget)
        
        # Add a button for adding new entries
        self.add_button = QPushButton("Add Entry", self)
        self.add_button.setToolTip("Inserts a new blank entry at the bottom of the character book")
        self.add_button.clicked.connect(self.add_entry)
        self.buttonWidgetLayout.addWidget(self.add_button)

        self.importWorldbookButton = QPushButton("Import Worldbook", self)
        self.importWorldbookButton.setToolTip("""Imports entries from a SillyTavern or Agnai worldbook, or an exported TavernAI
character's characterbook, and appends them to the existing character book's entries.""")
        self.importWorldbookButton.clicked.connect(self.import_worldbook)
        self.buttonWidgetLayout.addWidget(self.importWorldbookButton)

        self.view_checkbox.setChecked(True)

    def add_entry(self, entry=None):
        widget_item = QListWidgetItem(self.entries_list)
        custom_widget = EntryWidget(self.entries_list)
        custom_widget.setData(entry)
        custom_widget.complex_attributes.setVisible(not self.view_checkbox.isChecked())
        widget_item.setSizeHint(custom_widget.sizeHint())
        self.entries_list.addItem(widget_item)
        self.entries_list.setItemWidget(widget_item, custom_widget)
        custom_widget.delete_button.clicked.connect(lambda: self.delete_entry(widget_item))

    def import_worldbook(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        filepath = self.window().global_filepath
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", filepath, "JSON Files (*.json)", options=options)
        if fileName:
            with open(fileName, "r", encoding="utf-8") as f:
                worldBook = json.load(f)
                worldBook = process_worldbook(worldBook)
                if worldBook == None:
                    return
                characterBook = self.fullData["data"].get("character_book", {})
                self.fullData["data"]["character_book"] = characterBook
                import_worldbook(characterBook, worldBook)
                self.updateUIFromData()
    
    def delete_entry(self, item):
        row = self.entries_list.row(item)
        self.entries_list.takeItem(row)

    def toggle_view(self, state):
        # Toggle the visibility of certain fields based on the checkbox state
        self.complex_attributes.setVisible(state == Qt.Unchecked)
        self.extensions_form.setVisible(state == Qt.Unchecked)
        for i in range(self.entries_list.count()):
            item = self.entries_list.item(i)
            widget = self.entries_list.itemWidget(item)
            widget.complex_attributes.setVisible(state == Qt.Unchecked)
            sizeHint = widget.sizeHint()
            item.setSizeHint(sizeHint)
        self.entries_list.updateGeometry()

    def updateUIFromData(self):
        characterBook = self.fullData["data"].get("character_book", {})
        self.name_field.setText(characterBook.get("name", ""))
        self.description_field.setPlainText(characterBook.get("description", ""))
        self.scan_depth_editor.setText(str(characterBook.get("scan_depth", "")))
        self.token_budget_editor.setText(str(characterBook.get("token_budget", "")))
        self.recursive_scanning.setCheckState(convertBoolToTristate(characterBook.get("recursive_scanning", None)))
        self.extensions_edit.setPlainText(json.dumps(characterBook.get("extensions", {})))
        
        #initialize entries
        self.entries_list.clear()
        for entry in characterBook.get("entries", []):
            self.add_entry(entry)

    def updateDataFromUI(self):
        characterBook = self.fullData["data"].get("character_book", {})
        self.fullData["data"]["character_book"] = characterBook

        updateOrDeleteKey(characterBook, "name", self.name_field.text(), "")
        updateOrDeleteKey(characterBook, "description", self.description_field.toPlainText(), "")
        if self.scan_depth_editor.text() != "":
            characterBook["scan_depth"] = int(self.scan_depth_editor.text())
        elif "scan_depth" in characterBook:
            del characterBook["scan_depth"]
        if self.token_budget_editor.text() != "":
            characterBook["token_budget"] = int(self.token_budget_editor.text())
        elif "token_budget" in characterBook:
            del characterBook["token_budget"]
        updateOrDeleteKey(characterBook, "recursive_scanning", convertTristateToBool(self.recursive_scanning.checkState()))
        characterBook["extensions"] = safeJSONLoads(self.extensions_edit.toPlainText())
        
        entries = []
        for i in range(self.entries_list.count()):
            item = self.entries_list.item(i)
            entry = self.entries_list.itemWidget(item)
            entries.append(entry.getData())
        characterBook["entries"] = entries


class EditorWidget(QWidget):
    def __init__(self, fullData, filePath, parent=None):
        super().__init__(parent)
        
        self.fullData = fullData
        self.filePath = filePath
        
        self.tab_widget = QTabWidget()

        # Create the tabs
        self.tabCommon = QWidget(self.tab_widget)
        self.tabUncommon = QWidget(self.tab_widget)
        self.tabCharacterBook = QWidget(self.tab_widget)

        # Add tabs
        self.tab_widget.addTab(self.tabCommon, "Common Fields")
        self.tab_widget.addTab(self.tabUncommon, "Uncommon Fields")
        self.tab_widget.addTab(self.tabCharacterBook, "Character Book")

        # Create first tab layout
        self.tabCommon_layout = QFormLayout(self.tabCommon)
        self.nameEdit = QLineEdit()
        self.nameEdit.setToolTip("""Keep it short! The user will probably have to type it a lot.""")
        self.tabCommon_layout.addRow("Name", self.nameEdit)
        self.descriptionEdit = QPlainTextEdit()
        self.descriptionEdit.setToolTip(
            """Will be included in every prompt. A detailed description of the most important information the model
needs to know about the character. A thorough description is somewhere in the range of 300-800 tokens,
and probably should not exceed 1000 tokens.""")
        self.tabCommon_layout.addRow("Description", self.descriptionEdit)
        self.personalityEdit = QPlainTextEdit()
        self.personalityEdit.setToolTip("""A very brief summary of the character's personality.""")
        self.tabCommon_layout.addRow("Personality", self.personalityEdit)
        self.scenarioEdit = QPlainTextEdit()
        self.scenarioEdit.setToolTip("""A very brief summary of the current circumstances to the conversation.""")
        self.tabCommon_layout.addRow("Scenario", self.scenarioEdit)
        self.firstMesEdit = QPlainTextEdit()
        self.firstMesEdit.setToolTip(
            """A good first message can make a huge difference in the length and quality of the bot's responses.
write this greeting as if the bot had written it. Avoid describing the user's actions and dialogue too
much or the bot might act and speak for the user in subsequent responses.""")
        self.tabCommon_layout.addRow("First Message", self.firstMesEdit)
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
        self.tabCommon_layout.addRow("Message Example", self.mesExampleEdit)

        # Create second tab layout
        self.tabUncommon_layout = QGridLayout(self.tabUncommon)

        self.tabUncommon_layout.addWidget(QLabel("Alternate Greetings", self.tabUncommon), 0, 0)
        self.alternateGreetingsList = QListWidget(self.tabUncommon)
        self.alternateGreetingsList.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.alternateGreetingsList.setToolTip(
            """This list can contain any number of alternative first messages for this character.
Frontends should offer the ability for the user to select which first message to use when starting a
new conversation.""")
        self.tabUncommon_layout.addWidget(self.alternateGreetingsList)
        self.addAlternateGreetingButton = QPushButton("Add Alternate Greeting", self.tabUncommon)
        self.addAlternateGreetingButton.clicked.connect(self.add_alternate_greeting)
        self.tabUncommon_layout.addWidget(self.addAlternateGreetingButton, 1, 1, 1, 3)
        self.tabUncommon_layout.addWidget(self.alternateGreetingsList, 0, 1, 1, 3)

        self.tabUncommon_layout.addWidget(QLabel("System Prompt", self.tabUncommon), 2, 0)
        self.systemPromptEdit = QPlainTextEdit(self.tabUncommon)
        self.systemPromptEdit.setToolTip(
            """Frontends replace what users understand to be the "system prompt" global setting with the
value inside this field. The {{original}} placeholder can be used in this text, which is replaced with
the system prompt string that the frontend would have used in the absence of a character system_prompt
(e.g. the user's own system prompt).""")
        self.tabUncommon_layout.addWidget(self.systemPromptEdit, 2, 1, 1, 3)
        self.tabUncommon_layout.addWidget(QLabel("Post History Instructions", self.tabUncommon), 3, 0)
        self.postHistoryInstructionsEdit = QPlainTextEdit(self.tabUncommon)
        self.postHistoryInstructionsEdit.setToolTip(
            """Frontends replace what users understand to be the "ujb/jailbreak" setting with the value inside
this field. The {{original}} placeholder can be used in this text, which is replaced with the
"ujb/jailbreak" string that the frontend would have used in the absence of a character system_prompt
(e.g. the user's own ujb/jailbreak).""")
        self.tabUncommon_layout.addWidget(self.postHistoryInstructionsEdit, 3, 1, 1, 3)
        self.tabUncommon_layout.addWidget(QLabel("Tags", self.tabUncommon), 4, 0)
        self.tagsList = QLineEdit(self.tabUncommon)
        self.tagsList.setToolTip("""comma, separated, list, of, tags. Used for discoverability, isn't used by the chatbot.""")
        self.tabUncommon_layout.addWidget(self.tagsList, 4, 1, 1, 3)
        self.tabUncommon_layout.addWidget(QLabel("Character Version", self.tabUncommon), 5, 0)
        self.characterVersionEdit = QLineEdit(self.tabUncommon)
        self.characterVersionEdit.setToolTip("""A version string for tracking updates to this character.""")
        self.tabUncommon_layout.addWidget(self.characterVersionEdit, 5, 1)
        self.tabUncommon_layout.addWidget(QLabel("Creator", self.tabUncommon), 5, 2)
        self.creatorEdit = QLineEdit(self.tabUncommon)
        self.creatorEdit.setToolTip("""The name of the person who created this character.""")
        self.tabUncommon_layout.addWidget(self.creatorEdit, 5, 3)
        self.tabUncommon_layout.addWidget(QLabel("Creator Notes", self.tabUncommon), 6, 0)
        self.creatorNotesEdit = QPlainTextEdit(self.tabUncommon)
        self.creatorNotesEdit.setToolTip(
            """The text in this field is used for 'discoverability.' The first line might be a very simple
description of the bot - 'A friendly clown with a knife, in a dark alley'. Expect most users to only
see that first line. The rest of this value can be used for important notes the user may find helpful
to get the best experience from the bot.""")
        self.tabUncommon_layout.addWidget(self.creatorNotesEdit, 6, 1, 1, 3)
        self.tabUncommon_layout.addWidget(QLabel("Extensions", self.tabUncommon), 7, 0)
        self.extensionsEdit = QPlainTextEdit(self.tabUncommon)
        self.extensionsEdit.setMaximumHeight(PLAINTEXT_EDITOR_MAX_HEIGHT)
        self.extensionsEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.extensionsEdit.setToolTip("A block of JSON values used by non-standard chatbot extensions.")
        self.tabUncommon_layout.addWidget(self.extensionsEdit, 7, 1, 1, 3)        

        # Create third tab layout
        self.tabCharacterBook_layout = QVBoxLayout(self.tabCharacterBook)
        self.characterBookEdit = CharacterBookWidget(self.fullData)
        self.tabCharacterBook_layout.addWidget(self.characterBookEdit)

        self.updateUIFromData()

        # Create the buttons
        self.saveButton = QPushButton("Save")
        self.saveButton.setToolTip("""Updates the character data stored in the character card PNG.""")
        self.saveButton.root = self
        self.saveButton.clicked.connect(self.saveClicked)
        self.exportButton = QPushButton('Export JSON')
        self.exportButton.setToolTip("""Saves the data for this character as a separate JSON file. Doesn't update the character card PNG.""")
        self.exportButton.root = self
        self.exportButton.clicked.connect(self.exportClicked)
        self.importButton = QPushButton('Import JSON')
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
        self.extensionsEdit.setPlainText(json.dumps(data.get("extensions")))

        self.characterBookEdit.updateUIFromData()

    def updateDataFromUI(self):
        fullData = self.fullData
        data = fullData["data"]

        data["name"] = str(self.nameEdit.text())
        data["tags"] = [x.strip() for x in str(self.tagsList.text()).split(',')]
        if "" in data["tags"]:
            data["tags"].remove("")
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
        data["extensions"] = safeJSONLoads(self.extensionsEdit.toPlainText())
        
        self.characterBookEdit.updateDataFromUI()

    def saveClicked(self):
        self.updateDataFromUI()
        write_character(self.filePath, self.fullData)

    def exportClicked(self):
        self.updateDataFromUI()
        jsonFilepath = self.filePath[:-3]+"json"
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()", jsonFilepath, "JSON Files (*.json)", options=options)
        if fileName:
            with open(fileName, "w", encoding="utf-8") as f:
                json.dump(self.fullData, f)

    def importClicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        filepath = self.window().global_filepath
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", filepath, "JSON Files (*.json)", options=options)
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
    def __init__(self, imagePath, data):
        super().__init__()
        layout = QHBoxLayout()
        self.setLayout(layout)
        imageLabel = AspectRatioLabel(imagePath)
        imageLabel.setFixedSize(QSize(64, 64))
        layout.addWidget(imageLabel)

        text = QWidget(self)
        text_layout = QVBoxLayout(text)
        layout.addWidget(text)
        
        nameLabel = QLabel(data["data"].get("name", ""), text)
        text_layout.addWidget(nameLabel)
        textLabel = QLabel(os.path.basename(imagePath), text)
        text_layout.addWidget(textLabel)

class ImageList(QListWidget):
    directoryChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemClicked.connect(self.showImage)
        self.stack = QStackedWidget()
        self.loadImages()

    def loadImages(self):
        self.clear()
        self.stack = QStackedWidget()
        filepath = self.window().global_filepath
        for file in os.listdir(filepath):
            if file.endswith(".png"):
                item = QListWidgetItem(self)
                self.addItem(item)
                imagePath = os.path.join(filepath, file)
                data = read_character(imagePath)
                imageLabel = ImageThumbnail(imagePath, data)
                item.setSizeHint(imageLabel.sizeHint())
                self.setItemWidget(item, imageLabel)
                self.stack.addWidget(EditorWidget(data, imagePath, self))

    def showImage(self, item):
        index = self.row(item)
        self.stack.setCurrentIndex(index)
        self.stack.currentWidget().show()

    def changeDirectory(self):
        newDirpath = QFileDialog.getExistingDirectory(self, "Select Directory")
        if newDirpath != '':
            self.window().global_filepath = newDirpath
            self.updateDirectory()

    def updateDirectory(self):
        self.loadImages()
        self.directoryChanged.emit()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TavernAI Character Editor")
        self.global_filepath = "."
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)
        self.imageList = ImageList(self)
        self.imageList.directoryChanged.connect(self.updateStack)
        self.changeDirButton = QPushButton("Change Directory", self)
        self.changeDirButton.setToolTip("""Switches thumbnail list to another directory.
WARNING: Save your work first! Unsaved edits are discarded.""")
        self.changeDirButton.clicked.connect(self.imageList.changeDirectory)
        self.refreshDirButton = QPushButton("Refresh", self)
        self.refreshDirButton.setToolTip("""Reloads the thumbnail list for the current directory.
WARNING: Save your work first! Unsaved edits are discarded.""")
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
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

