from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Case, When, IntegerField
from .models import Macro, MacroVote, MacroCollection, CubaseVersion
from .utils import KeyCommandsParser


class MacroUploadForm(forms.Form):
    """Form for uploading Macros files (Key Commands.xml) - file is only used for parsing, never stored"""
    
    file = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': '.xml'
        })
    )
    
    cubase_version = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the Cubase version this file was created with.'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ensure CubaseVersion objects exist - auto-populate if empty
        if not CubaseVersion.objects.exists():
            self._populate_cubase_versions()
        
        # Order queryset: Unspecified (major=0) first, then others by version descending
        queryset = CubaseVersion.objects.all().annotate(
            sort_order=Case(
                When(major_version=0, then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('sort_order', '-major_version')
        self.fields['cubase_version'].queryset = queryset
        self.fields['cubase_version'].empty_label = None  # Remove empty label since we have "Unspecified"
        
        # Set default to "Unspecified"
        try:
            unspecified_version = CubaseVersion.objects.get(version='Unspecified')
            self.fields['cubase_version'].initial = unspecified_version
        except CubaseVersion.DoesNotExist:
            # If Unspecified doesn't exist, try to create it
            unspecified_version = CubaseVersion.objects.create(
                version='Unspecified',
                major_version=0
            )
            self.fields['cubase_version'].initial = unspecified_version
    
    def _populate_cubase_versions(self):
        """Auto-populate CubaseVersion objects if they don't exist"""
        versions = []
        
        # Add "Unspecified" as the default option (with major=0 so it sorts first)
        versions.append({
            'version': 'Unspecified',
            'major': 0,
        })
        
        # Add "Cubase 4 or older" option
        versions.append({
            'version': 'Cubase 4 or older',
            'major': 4,
        })
        
        # Generate major versions 5-15
        for major in range(5, 16):  # 5 to 15 inclusive
            versions.append({
                'version': f'Cubase {major}',
                'major': major,
            })
        
        # Create versions that don't exist
        for version_data in versions:
            CubaseVersion.objects.get_or_create(
                version=version_data['version'],
                defaults={
                    'major_version': version_data['major'],
                }
            )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 10MB.")
            
            # Check file extension
            if not file.name.lower().endswith('.xml'):
                raise ValidationError("Only XML files are allowed.")
            
            # Validate XML content
            try:
                file.seek(0)  # Reset file pointer
                content = file.read().decode('utf-8')
                file.seek(0)  # Reset again for later use
                
                # Basic XML validation
                try:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(content)
                    
                    # Check if it's a Key Commands file
                    if root.tag != 'KeyCommands':
                        raise ValidationError("Invalid Macros file (Key Commands.xml): Root element must be 'KeyCommands'")
                    
                    # Check for either Macros or Categories section (both are valid Cubase formats)
                    macros_list = root.find(".//list[@name='Macros']")
                    categories_list = root.find(".//list[@name='Categories']")
                    
                    if macros_list is None and categories_list is None:
                        raise ValidationError("Invalid Macros file (Key Commands.xml): No Macros or Categories section found")
                    
                    # Check if there are any items in whichever section exists
                    items_found = False
                    if macros_list is not None:
                        macro_items = macros_list.findall("item")
                        items_found = len(macro_items) > 0
                    
                    if categories_list is not None and not items_found:
                        category_items = categories_list.findall("item")
                        items_found = len(category_items) > 0
                        
                    if not items_found:
                        raise ValidationError("Invalid Macros file (Key Commands.xml): No macros or categories found")
                        
                except ET.ParseError as pe:
                    raise ValidationError(f"Invalid XML format: {pe}")
                    
            except UnicodeDecodeError:
                raise ValidationError("File must be a valid UTF-8 encoded XML file.")
            except ValidationError:
                raise  # Re-raise validation errors
            except Exception as e:
                raise ValidationError(f"Error validating file: {str(e)}")
        
        return file


class MacroForm(forms.ModelForm):
    """Form for editing individual macros"""
    
    class Meta:
        model = Macro
        fields = ['name', 'description', 'key_binding', 'is_private']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Macro name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe what this macro does (optional)'
            }),
            'key_binding': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Ctrl+Alt+M'
            }),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'Name of the macro/command.',
            'description': 'Optional description of what this macro does.',
            'key_binding': 'Keyboard shortcut for this macro.',
            'is_private': 'Check to keep this macro private (only visible to you). Uncheck to make it public.',
        }


class MacroVoteForm(forms.ModelForm):
    """Form for voting/rating macros"""
    
    class Meta:
        model = MacroVote
        fields = ['rating']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'rating': 'Rate this macro from 1 to 5 stars.',
        }


class MacroCollectionForm(forms.ModelForm):
    """Form for creating macro collections"""
    
    class Meta:
        model = MacroCollection
        fields = ['name', 'description', 'is_private']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Collection name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe this collection of macros'
            }),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'Name for your macro collection.',
            'description': 'Describe what type of macros are in this collection.',
            'is_private': 'Check to keep this collection private (only visible to you). Uncheck to make it public.',
        }


class MacroSearchForm(forms.Form):
    """Form for searching macros"""
    SORT_CHOICES = [
        ('newest', 'Newest First'),
        ('oldest', 'Oldest First'),
        ('most_popular', 'Most Popular'),
        ('highest_rated', 'Highest Rated'),
        ('most_downloaded', 'Most Downloaded'),
        ('alphabetical', 'Alphabetical'),
    ]
    
    query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search macros...'
        })
    )
    
    cubase_version = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        empty_label="All Versions",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='newest',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    has_key_binding = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cubase_version'].queryset = CubaseVersion.objects.all()


class CubaseVersionForm(forms.ModelForm):
    """Form for adding new Cubase versions"""
    
    class Meta:
        model = CubaseVersion
        fields = ['version', 'major_version']
        widgets = {
            'version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Cubase 13'
            }),
            'major_version': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '13'
            }),
        }
        help_texts = {
            'version': 'Full version string as it appears in Cubase.',
            'major_version': 'Major version number only.',
        }


class MacroSelectionForm(forms.Form):
    """Form for selecting macros to include in a download"""
    
    def __init__(self, macros, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for macro in macros:
            field_name = f'macro_{macro.id}'
            self.fields[field_name] = forms.BooleanField(
                required=False,
                label=macro.name,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            ) 