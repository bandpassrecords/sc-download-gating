import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional
import logging
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class KeyCommandsParser:
    """Parser for Cubase Key Commands XML files"""
    
    def __init__(self, file_path_or_content):
        """
        Initialize parser with file path or content
        
        Args:
            file_path_or_content: Either a file path string or XML content string
        """
        self.file_path_or_content = file_path_or_content
        self.root = None
        self.categories = {}
        self.commands = []
    
    def parse(self) -> Dict[str, List[Dict]]:
        """
        Parse the Key Commands XML file
        
        Returns:
            Dictionary with categories as keys and lists of commands as values
        """
        try:
            # Parse XML content
            if isinstance(self.file_path_or_content, str):
                # Check if it's XML content (starts with <?xml or <KeyCommands)
                if self.file_path_or_content.strip().startswith('<?xml') or self.file_path_or_content.strip().startswith('<KeyCommands'):
                    # It's XML content string
                    self.root = ET.fromstring(self.file_path_or_content)
                else:
                    # Try as file path
                    tree = ET.parse(self.file_path_or_content)
                    self.root = tree.getroot()
            else:
                # It's a file path
                tree = ET.parse(self.file_path_or_content)
                self.root = tree.getroot()
            
            # Validate root element
            if self.root.tag != 'KeyCommands':
                raise ValidationError("Invalid Key Commands file: Root element must be 'KeyCommands'")
            
            # Extract categories and commands
            self._extract_categories()
            
            return self.categories
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise ValidationError(f"Invalid XML format: {e}")
        except Exception as e:
            logger.error(f"Error parsing Key Commands file: {e}")
            raise ValidationError(f"Error parsing file: {e}")
    
    def _extract_categories(self):
        """Extract macros from both traditional Categories and new Macros structure"""
        # Try to find Macros list first (new format)
        macros_list = self.root.find(".//list[@name='Macros']")
        
        if macros_list is not None:
            # New Macros format - each item is a complete macro
            self._process_macros_list(macros_list)
        else:
            # Traditional Categories format - nested structure
            categories_list = self.root.find(".//list[@name='Categories']")
            if categories_list is not None:
                self._process_categories_list(categories_list)
            else:
                raise ValidationError("No macros or categories found in Key Commands file")
    
    def _process_macros_list(self, macros_list):
        """Process the new Macros format"""
        for macro_item in macros_list.findall("item"):
            macro_data = self._extract_macro_data(macro_item)
            
            if macro_data:
                # Group by category for backward compatibility
                category_name = macro_data.get('category', 'Uncategorized')
                
                if category_name not in self.categories:
                    self.categories[category_name] = []
                
                self.categories[category_name].append(macro_data)
    
    def _process_categories_list(self, categories_list):
        """Process the traditional Categories format"""
        for category_item in categories_list.findall("item"):
            category_name_elem = category_item.find("string[@name='Name']")
            
            if category_name_elem is None:
                continue
                
            category_name = category_name_elem.get('value', '').strip()
            
            if not category_name:
                continue
            
            # Find commands list for this category
            commands_list = category_item.find("list[@name='Commands']")
            
            if commands_list is None:
                continue
            
            # Extract commands for this category and treat each as a macro
            for command_item in commands_list.findall("item"):
                command_data = self._extract_command_data(command_item, category_name)
                
                if command_data:
                    if category_name not in self.categories:
                        self.categories[category_name] = []
                    
                    self.categories[category_name].append(command_data)
    

    
    def _extract_macro_data(self, macro_item) -> Optional[Dict]:
        """Extract data for a single macro from the real Cubase Macros structure"""
        # Get macro name
        name_elem = macro_item.find("string[@name='Name']")
        
        if name_elem is None:
            return None
        
        macro_name = name_elem.get('value', '').strip()
        
        if not macro_name:
            return None
        
        # Get the commands list for this macro
        commands_list = macro_item.find("list[@name='Commands']")
        
        if commands_list is None:
            return None
        
        # Extract all commands that make up this macro
        commands = []
        categories = set()
        
        for command_item in commands_list.findall("item"):
            category_elem = command_item.find("string[@name='Category']")
            command_name_elem = command_item.find("string[@name='Name']")
            
            if category_elem is not None and command_name_elem is not None:
                category = category_elem.get('value', '').strip()
                command_name = command_name_elem.get('value', '').strip()
                
                if category and command_name:
                    commands.append({
                        'category': category,
                        'name': command_name
                    })
                    categories.add(category)
        
        if not commands:
            return None
        
        # Use the most common category, or "Mixed" if multiple categories
        if len(categories) == 1:
            primary_category = list(categories)[0]
        else:
            primary_category = "Mixed"
        
        # Create a description from the commands
        description = f"Macro with {len(commands)} commands: " + ", ".join([cmd['name'] for cmd in commands[:3]])
        if len(commands) > 3:
            description += f" and {len(commands) - 3} more"
        
        # Capture the original XML snippet (macro definition)
        xml_snippet = ET.tostring(macro_item, encoding='unicode', method='xml')
        
        # Create the reference snippet (for Commands list)
        reference_item = ET.Element('item')
        ET.SubElement(reference_item, 'string', name='Name', value=macro_name)
        reference_snippet = ET.tostring(reference_item, encoding='unicode', method='xml')
        
        macro_data = {
            'name': macro_name,
            'category': primary_category,
            'description': description,
            'key_bindings': [],  # Macros typically don't have direct key bindings
            'commands': commands,  # Store the actual commands for reference
            'xml_snippet': xml_snippet,  # Store the macro definition XML snippet (from <list name="Macros">)
            'reference_snippet': reference_snippet  # Store the macro reference XML snippet (for <list name="Commands">)
        }
        
        return macro_data
    
    def _extract_command_data(self, command_item, category_name):
        """Extract data for a single command from traditional Categories structure"""
        # Get command name
        name_elem = command_item.find("string[@name='Name']")
        
        if name_elem is None:
            return None
        
        command_name = name_elem.get('value', '').strip()
        
        if not command_name:
            return None
        
        # Get key binding if available
        key_elem = command_item.find("string[@name='Key']")
        key_binding = key_elem.get('value', '').strip() if key_elem is not None else ''
        
        # Create both XML snippets for traditional commands
        command_item_xml = ET.tostring(command_item, encoding='unicode', method='xml')
        
        # Create reference snippet
        reference_item = ET.Element('item')
        ET.SubElement(reference_item, 'string', name='Name', value=command_name)
        reference_snippet = ET.tostring(reference_item, encoding='unicode', method='xml')
        
        # Create macro-like data structure for traditional commands
        command_data = {
            'name': command_name,
            'category': category_name,
            'description': f"Command from {category_name} category",
            'key_bindings': [key_binding] if key_binding else [],
            'commands': [],  # Traditional commands don't have sub-commands
            'xml_snippet': command_item_xml,  # Store the command definition
            'reference_snippet': reference_snippet  # Store the command reference
        }
        
        return command_data

 
    
    def get_all_macros(self) -> List[Dict]:
        """Get all macros as a flat list with category information"""
        all_macros = []
        
        for category_name, macros in self.categories.items():
            for macro in macros:
                macro_with_category = macro.copy()
                macro_with_category['category'] = category_name
                all_macros.append(macro_with_category)
        
        return all_macros
    
    def get_categories_count(self) -> int:
        """Get total number of categories"""
        return len(self.categories)
    
    def get_commands_count(self) -> int:
        """Get total number of commands"""
        return sum(len(commands) for commands in self.categories.values())
    
    def validate_file(self) -> Tuple[bool, str]:
        """
        Validate if the file is a proper Key Commands XML file
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self.parse()
            
            if self.get_categories_count() == 0:
                return False, "No categories found in file"
            
            if self.get_commands_count() == 0:
                return False, "No commands found in file"
            
            return True, "Valid Key Commands file"
            
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {e}"


def create_keycommands_xml(selected_macros: List[Dict], base_structure: Optional[str] = None) -> str:
    """
    Create a new Key Commands XML file with selected macros in the real Cubase Macros format
    
    Args:
        selected_macros: List of macro dictionaries with commands, category, name, description
        base_structure: Optional base XML structure to build upon
        
    Returns:
        Generated XML content as string
    """
    # Create root element
    root = ET.Element("KeyCommands")
    
    # Create macros list
    macros_list = ET.SubElement(root, "list")
    macros_list.set("name", "Macros")
    macros_list.set("type", "list")
    
    # Add each macro as a direct item
    for macro in selected_macros:
        macro_item = ET.SubElement(macros_list, "item")
        
        # Macro name
        name_elem = ET.SubElement(macro_item, "string")
        name_elem.set("name", "Name")
        name_elem.set("value", macro.get('name', ''))
        
        # Commands list for this macro
        commands_list = ET.SubElement(macro_item, "list")
        commands_list.set("name", "Commands")
        commands_list.set("type", "list")
        
        # Add the commands that make up this macro
        commands = macro.get('commands', [])
        if not commands:
            # If no commands stored, create a dummy command as placeholder
            commands = [{'category': macro.get('category', 'Uncategorized'), 'name': macro.get('name', '')}]
        
        for command in commands:
            command_item = ET.SubElement(commands_list, "item")
            
            # Command category
            category_elem = ET.SubElement(command_item, "string")
            category_elem.set("name", "Category")
            category_elem.set("value", command.get('category', ''))
            
            # Command name
            command_name_elem = ET.SubElement(command_item, "string")
            command_name_elem.set("name", "Name")
            command_name_elem.set("value", command.get('name', ''))
    
    # Convert to string with proper XML declaration
    xml_str = ET.tostring(root, encoding='unicode', method='xml')
    
    # Add XML declaration
    full_xml = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_str
    
    return full_xml


def create_keycommands_xml_with_embedded_macros(existing_root, selected_macros):
    """
    Embed selected macros into an existing Key Commands XML root element.
    
    This function:
    1. Adds macro definitions to <list name="Macros" type="list">
    2. Adds macro references to <list name="Commands" type="list"> under the Macro item
    
    Args:
        existing_root: The root ElementTree element of the user's Key Commands.xml file.
        selected_macros: QuerySet of Macro objects to embed
        
    Returns:
        Generated XML content as string with embedded macros
    """
    try:
        root = existing_root
        
        # STEP 1: Find or create the Macros list for macro definitions
        macros_list = root.find('list[@name="Macros"]')
        if macros_list is None:
            macros_list = ET.SubElement(root, "list")
            macros_list.set("name", "Macros")
            macros_list.set("type", "list")
        
        # STEP 2: Add each selected macro definition to the Macros list
        for macro in selected_macros:
            if macro.xml_snippet:
                # Parse and add the macro's XML snippet
                try:
                    macro_element = ET.fromstring(macro.xml_snippet)
                    macros_list.append(macro_element)
                except ET.ParseError as e:
                    logger.warning(f"Failed to parse XML snippet for macro {macro.name}: {e}")
                    # Create a basic macro structure as fallback
                    _create_fallback_macro_element(macros_list, macro)
            else:
                # No XML snippet, create from stored data
                _create_fallback_macro_element(macros_list, macro)
        
        # STEP 3: Find or create the Commands list for macro references
        commands_list = None

        # Navigate to the categories list
        categories_list = root.find('list[@name="Categories"]')

        if categories_list is not None:
            # Find or create Macro category item
            macro_category_item = None
            for item in categories_list.findall('item'):
                name_string = item.find('string[@name="Name"]')
                if name_string is not None and name_string.attrib.get('value') == "Macro":
                    macro_category_item = item
                    break
            
            if macro_category_item is None:
                macro_category_item = ET.SubElement(categories_list, "item")
                ET.SubElement(macro_category_item, "string", name="Name", value="Macro")
            
            commands_list = macro_category_item.find('list[@name="Commands"]')
            if commands_list is None:
                commands_list = ET.SubElement(macro_category_item, "list")
                commands_list.set("name", "Commands")
                commands_list.set("type", "list")
        
        # STEP 4: Add simple references to each selected macro in the Commands/Macro list
        # Use stored reference_snippet if available, otherwise generate it
        if commands_list is not None:
            for macro in selected_macros:
                if macro.reference_snippet:
                    # Use stored reference snippet
                    try:
                        ref_element = ET.fromstring(macro.reference_snippet)
                        commands_list.append(ref_element)
                    except ET.ParseError:
                        # Fallback: create simple reference
                        macro_ref_item = ET.SubElement(commands_list, 'item')
                        ET.SubElement(macro_ref_item, 'string', name='Name', value=macro.name)
                else:
                    # Generate reference if not stored
                    macro_ref_item = ET.SubElement(commands_list, 'item')
                    ET.SubElement(macro_ref_item, 'string', name='Name', value=macro.name)
        
        # Convert back to XML string
        xml_string = ET.tostring(root, encoding='unicode', method='xml')
        
        # Add XML declaration if not present
        if not xml_string.startswith('<?xml'):
            xml_string = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_string
        
        return xml_string
        
    except Exception as e:
        logger.error(f"Error creating XML with embedded macros: {e}")
        raise ValidationError(f"Failed to create XML file: {str(e)}")


def _create_fallback_macro_element(macros_list, macro):
    """Create a fallback macro element when XML snippet is not available"""
    macro_item = ET.SubElement(macros_list, 'item')
    ET.SubElement(macro_item, 'string', name='Name', value=macro.name)
    commands_list = ET.SubElement(macro_item, 'list', name='Commands', type='list')
    
    # Add commands from the stored JSON
    for command in macro.commands:
        command_item = ET.SubElement(commands_list, 'item')
        ET.SubElement(command_item, 'string', name='Category', value=command.get('category', ''))
        ET.SubElement(command_item, 'string', name='Name', value=command.get('name', ''))


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip 