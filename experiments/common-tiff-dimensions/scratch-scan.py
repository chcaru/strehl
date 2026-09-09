"""Scratch-only strict resolution for the held, non-atomic M194h scanner.

Caller authenticates both source files before use.  This factory does not mutate
the held module.  Only the controller's exact declared build target may select
the cloned scanner; retained evidence keeps the original scanner.
"""
from types import FunctionType


def make_scanner(held, target):
    """Return the strict-retained / strict-resolving-scratch dispatcher."""
    original = held.scan
    need = held.need
    lexical = held.lexical
    Path = original.__globals__["Path"]
    os = original.__globals__["os"]
    stat = original.__globals__["stat"]
    repository = held.ROOT
    target = Path(target)
    need(target.is_absolute() and target == lexical(target),
         "absolute lexical scratch root")
    need(target != repository and target.is_relative_to(repository),
         "repository-owned scratch root")
    need(type(original) is FunctionType and original.__closure__ is None,
         "held scanner has no free variables")

    def scratch_owned(path):
        path = Path(os.path.abspath(path))
        need(len(str(path)) <= 384 and str(path).isascii(),
             "declared ASCII path width")
        # Unlike exists(), lstat sees a present dangling reparse/symlink.
        # Continue past an absent component to inspect every other ancestor;
        # strict resolve below remains the source of the final missing-path error.
        for part in (path, *path.parents):
            try:
                observed = part.lstat()
            except FileNotFoundError:
                continue
            need(not observed.st_file_attributes & 0x400
                 and not stat.S_ISLNK(observed.st_mode), "reparse/symlink path")
        need(path.is_relative_to(repository), "repository-owned path")
        need(path.is_relative_to(target), "declared scratch containment")
        # Missing entries remain FileNotFoundError.  The held scanner alone
        # decides whether that exact exception is eligible for scratch recovery.
        resolved = path.resolve(strict=True)
        need(resolved == path,
             f"canonical scratch path declared={str(path)!r} resolved={str(resolved)!r}")
        return path

    namespace = dict(original.__globals__)
    namespace["owned"] = scratch_owned
    scratch = FunctionType(original.__code__, namespace, original.__name__,
                           original.__defaults__, original.__closure__)
    scratch.__kwdefaults__ = (None if original.__kwdefaults__ is None
                             else dict(original.__kwdefaults__))

    def scan(root, limit, *, tolerate_disappearance=False):
        need(type(tolerate_disappearance) is bool, "typed scratch scan policy")
        if not tolerate_disappearance:
            return original(root, limit, tolerate_disappearance=False)
        need(Path(root) == target, "exact declared scratch scan root")
        return scratch(root, limit, tolerate_disappearance=True)

    return scan
