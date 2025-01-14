import os.path

from .deps import Fileset, Package, find_package
from .rdl import RdlPackage

__all__ = [
    'RtlPackage',
    ]

class RtlPackage(Package):
    def __init__(self, *args, verilator_executable=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._rtl = Fileset()
        self._top = None
        self._main = Fileset()
        self._waivers = Fileset()
        self._skip_lint = False
        self._verilator_executable = verilator_executable

    def rtl(self, paths):
        self._rtl.add(paths)

    def top(self, top_module=None):
        self._top = top_module or self.name()

    def waivers(self, waiver):
        self._waivers.add(waiver)

    def skip_lint(self):
        self._skip_lint = True

    def setup_outputs(self, *, target=None):
        if self._verilator_executable:
            assert target is not None

            self.make_flags.cov
            self.make_flags.fst
            self.make_flags.lto
            self.make_flags.opt
            self.make_flags.prof
            self.make_flags.rand
            self.make_flags.threads
            self.make_flags.trace

            self.add_outputs([self._verilator_executable])

        if target:
            super().setup_outputs(target=target)
        else:
            self.add_outputs(['lint.stamp'])
            super().setup_outputs(target='lint')

        if self._verilator_executable:
            self.copy_object(self, os.path.join('vl', 'Vtop'), self._verilator_executable)

    def link_dependency(self, dependency):
        # By default, subclasses of RtlPackage cannot be .require()'d by RtlPackages
        if type(dependency) is RtlPackage:
            pass
        elif isinstance(dependency, RdlPackage):
            pass
        else:
            super().link_dependency(dependency)

    def print_vars(self):
        super().print_vars()

        rtl = self._all_rtl(for_lint=(self.target() == 'lint'))
        self.core_var('rtl_files', rtl)

        if self._top:
            self.core_var('rtl_top', self._top)

        self.copy_sources(self._main)
        self.core_var('vl_main', self._main)

        if self._verilator_executable:
            self.core_var('vl_exe_alias', self._verilator_executable)

    def _require_rtl_top(self):
        self.check_assert(self._top, 'missing top module, remember to call .top()')
        return self._top

    def _all_rtl(self, *, copy_to=None, for_lint=False):
        if not copy_to:
            copy_to = self

        rtl = self.walk_filesets(lambda package: isinstance(package, RtlPackage) and (not for_lint or not package._skip_lint),
                                 lambda package: package._rtl)

        copy_to.copy_sources(rtl)

        if not for_lint:
            regblock_rtl = self.walk_filesets(lambda package: isinstance(package, (RdlPackage, RtlPackage)),
                                              lambda package: copy_to.copy_outputs(package) if isinstance(package, RdlPackage) else Fileset())

            rtl.prepend(regblock_rtl)

            if not regblock_rtl.empty():
                intfs = find_package('peakrdl_intfs').resolve()
                interface_rtl = intfs._rtl

                rtl.prepend(interface_rtl)
                copy_to.copy_sources(interface_rtl)

                if self._verilator_executable:
                    lint_waivers = intfs._waivers

                    rtl.prepend(lint_waivers)
                    copy_to.copy_sources(lint_waivers)

        return rtl
