\set ON_ERROR_STOP on

DO $roles$
DECLARE
    role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY[
        'uwa_status',
        'uwa_staging',
        'uwa_activation',
        'uwa_runtime',
        'uwa_backup',
        'uwa_migration',
        'uwa_restore'
    ] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format(
                'CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
                role_name
            );
        END IF;
    END LOOP;
    FOREACH role_name IN ARRAY ARRAY[
        'uwa_status_login',
        'uwa_staging_login',
        'uwa_activation_login',
        'uwa_runtime_login',
        'uwa_backup_login',
        'uwa_migration_login'
    ] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format(
                'CREATE ROLE %I LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
                role_name
            );
        END IF;
    END LOOP;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'uwa_restore_login') THEN
        CREATE ROLE uwa_restore_login LOGIN NOINHERIT NOSUPERUSER NOCREATEDB
            NOCREATEROLE NOREPLICATION NOBYPASSRLS;
    END IF;
END
$roles$;

DO $role_attributes$
DECLARE
    role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY[
        'uwa_status',
        'uwa_staging',
        'uwa_activation',
        'uwa_runtime',
        'uwa_backup',
        'uwa_migration'
    ] LOOP
        EXECUTE format(
            'ALTER ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
            role_name
        );
    END LOOP;
    FOREACH role_name IN ARRAY ARRAY[
        'uwa_status_login',
        'uwa_staging_login',
        'uwa_activation_login',
        'uwa_runtime_login',
        'uwa_backup_login',
        'uwa_migration_login'
    ] LOOP
        EXECUTE format(
            'ALTER ROLE %I LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
            role_name
        );
    END LOOP;
END
$role_attributes$;

ALTER ROLE uwa_restore CREATEDB CREATEROLE NOLOGIN NOSUPERUSER NOREPLICATION NOBYPASSRLS;
ALTER ROLE uwa_restore_login LOGIN NOINHERIT NOSUPERUSER NOCREATEDB
    NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE uwa_restore_login SET log_statement = 'all';
ALTER ROLE uwa_restore_login SET log_duration = 'on';

GRANT uwa_status TO uwa_status_login;
GRANT uwa_staging TO uwa_staging_login;
GRANT uwa_activation TO uwa_activation_login;
GRANT uwa_runtime TO uwa_runtime_login;
GRANT uwa_backup TO uwa_backup_login;
GRANT uwa_migration TO uwa_migration_login;
GRANT uwa_restore TO uwa_restore_login;
GRANT uwa_migration, uwa_activation, uwa_backup TO uwa_restore;
GRANT pg_read_all_data TO uwa_backup;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO
    uwa_status, uwa_staging, uwa_activation, uwa_runtime, uwa_backup;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM
    uwa_status, uwa_staging, uwa_activation, uwa_runtime;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM
    uwa_status, uwa_staging, uwa_activation, uwa_runtime;
GRANT SELECT ON TABLE django_migrations TO
    uwa_status, uwa_staging, uwa_activation, uwa_runtime;

DO $database_grants$
BEGIN
    EXECUTE format(
        'GRANT CONNECT ON DATABASE %I TO uwa_status, uwa_staging, uwa_activation, uwa_runtime, uwa_backup, uwa_migration, uwa_restore',
        current_database()
    );
END
$database_grants$;

DO $watershed_grants$
DECLARE
    object record;
BEGIN
    FOR object IN
        SELECT c.relkind, n.nspname, c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'p')
          AND c.relname LIKE 'watershed\_%' ESCAPE '\'
    LOOP
        EXECUTE format('GRANT SELECT ON TABLE %I.%I TO uwa_status, uwa_staging', object.nspname, object.relname);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I.%I TO uwa_activation', object.nspname, object.relname);
    END LOOP;
    FOR object IN
        SELECT c.relkind, n.nspname, c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'S'
          AND c.relname LIKE 'watershed\_%' ESCAPE '\'
    LOOP
        EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %I.%I TO uwa_staging', object.nspname, object.relname);
        EXECUTE format('GRANT USAGE, SELECT, UPDATE ON SEQUENCE %I.%I TO uwa_activation', object.nspname, object.relname);
    END LOOP;
END
$watershed_grants$;

GRANT SELECT ON TABLE
    watershed_watershed,
    watershed_subcatchment,
    watershed_channel,
    watershed_watershedcollection,
    watershed_watershedidentity,
    watershed_watershedrunalias,
    watershed_datarelease,
    watershed_activedatarelease,
    watershed_datarunstate,
    watershed_dataartifactlineage,
    watershed_runcapability
TO uwa_runtime;

GRANT INSERT ON TABLE
    watershed_watershedcollection,
    watershed_watershedidentity,
    watershed_datarelease,
    watershed_datarunstate,
    watershed_dataartifactlineage,
    watershed_datareleaseattempt,
    watershed_datareleasestagingstate,
    watershed_stagedwatershed,
    watershed_stagedsubcatchment,
    watershed_stagedchannel,
    watershed_stagedruncapability
TO uwa_staging;
GRANT UPDATE ON TABLE
    watershed_datareleaseattempt,
    watershed_datareleasestagingstate,
    watershed_stagedwatershed,
    watershed_stagedsubcatchment,
    watershed_stagedchannel,
    watershed_stagedruncapability
TO uwa_staging;
GRANT DELETE ON TABLE
    watershed_datareleasestagingstate,
    watershed_stagedwatershed,
    watershed_stagedsubcatchment,
    watershed_stagedchannel,
    watershed_stagedruncapability
TO uwa_staging;
ALTER SCHEMA public OWNER TO uwa_migration;
DO $ownership$
DECLARE
    object record;
BEGIN
    FOR object IN
        SELECT c.relkind, n.nspname, c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'p')
          AND c.relname ~ '^(auth_|django_|silk_|watershed_)'
    LOOP
        EXECUTE format(
            'ALTER %s %I.%I OWNER TO uwa_migration',
            'TABLE',
            object.nspname,
            object.relname
        );
    END LOOP;
END
$ownership$;
