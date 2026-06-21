# V0-002c Sources CSV Import

Status: completed; superseded by `V0_002D_RESCAN_IDENTITY.md` for repeated scan
identity semantics.

This slice adds optional `sources.csv` import during `scan`. It does not create
media entities that are absent from the filesystem; it only annotates scanned
media records.

## Supported Columns

At least one location column is required:

```text
location
path
file
```

Optional annotation columns:

```text
source_type
media_type
work
role
rights_status
forbidden_by_user
notes
```

`media_type` is accepted as an alias for `source_type`.

## Behavior

- locations must be project-relative
- `./` prefixes are normalized
- invalid enum and boolean values become scan warnings
- annotations match any scanned duplicate location
- matching annotations raise source type, work, role, rights status, and notes to
  level 1 `sources_csv` assertions
- `forbidden_by_user=true` adds the `forbidden_by_user` risk flag
- `rights_status=restricted` adds the `rights_restricted` risk flag

## Still Out Of Scope

- creating SourceRecords for missing files listed only in CSV
- user confirmation history
- conflict resolution beyond warning invalid CSV values
- exporting normalized `sources.csv`
