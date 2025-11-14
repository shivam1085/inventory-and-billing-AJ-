import os
from django.conf import settings
from django.core.checks import register, Error


@register()
def production_database_check(app_configs, **kwargs):
    """
    Prevent accidental deployment on SQLite in production. If DEBUG is False
    and the default DB engine is sqlite3, raise a system check error so the
    build/deploy fails and surfaces the misconfiguration early.
    """
    errors = []
    try:
        # Allow an explicit bypass during builds or emergency maintenance
        # Set SKIP_DB_CHECK=true to suppress this check (not recommended for normal production)
        if os.environ.get('SKIP_DB_CHECK', '').lower() in ('1', 'true', 'yes'):
            return errors

        default_db = settings.DATABASES.get('default', {})
        engine = default_db.get('ENGINE', '')
        if not settings.DEBUG and 'sqlite3' in engine:
            errors.append(Error(
                'SQLite configured as default database in production.',
                hint='Set DATABASE_URL to a Postgres connection string on your host (Render/Neon/etc).',
                id='inventory.E001',
            ))
    except Exception:
        # If settings are not fully loaded, don't block startup here.
        pass
    return errors
