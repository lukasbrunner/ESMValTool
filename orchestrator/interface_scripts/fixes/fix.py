import importlib


class Fix(object):
    """
    Base class for fixes
    """
    def fix_file(self, filepath):
        return filepath

    def fix_metadata(self, cube):
        return cube

    def fix_data(self, cube):
        return cube

    @staticmethod
    def get_fix(project, model, variable):
        project = project.replace('-', '_')
        model = model.replace('-', '_')
        variable = variable.replace('-', '_')
        try:
            fix = importlib.import_module('orchestrator.interface_scripts.fixes.{0}.{1}'.format(project, model))
            fix = getattr(fix, variable)()
        except (AttributeError, ImportError):
            fix = None
        return fix
