# Reuse the shared SPA-shell context. Same bundle, different entry URL.
from diagnostic_management.www.diagnostic_management import get_context as _shared  # noqa: F401

no_cache = 1


def get_context(context):
	return _shared(context)
