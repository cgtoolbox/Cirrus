
class PluginFileNotFoundError(Exception):
    """ Raised if a given plugin file ( python ) is not found under the plugins folder
    """
    pass

class InvalidPluginFileMethodAlreadyExistError(Exception):
    """ Raise when two methods with the same name exist in a plugin file
    """
    pass

class InvalidPluginSettingsError(Exception):
    """ Raised when an error is found in plugin_settings.json formatting
    """
    pass

class InvalidGetMethodError(Exception):
    """ Raised when the get() method of PluginInfos is used with invalid arguments
    """
    pass