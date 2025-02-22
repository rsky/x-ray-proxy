-- name: SaveApiLog :exec
INSERT INTO
  api_log (
    bucket,
    object_key,
    member_id,
    host,
    method,
    path,
    params,
    raw_size,
    created_at
  )
VALUES
  (
    :bucket,
    :object_key,
    :member_id,
    :host,
    :method,
    :path,
    :params,
    :raw_size,
    CURRENT_TIMESTAMP
  );

-- name: ListApiLog :many
SELECT
  *
FROM
  api_log
WHERE
  (
    :path IS NULL
    OR path like :path
  )
  AND (
    :member_id IS NULL
    OR member_id = :member_id
  )
  AND rowid >= :cursor
  AND created_at >= :start_datetime
  AND created_at <= :end_datetime
ORDER BY
  rowid
LIMIT
  :limit;

-- name: ListApiLogDesc :many
SELECT
  *
FROM
  api_log
WHERE
  (
    :path IS NULL
    OR path like :path
  )
  AND (
    :member_id IS NULL
    OR member_id = :member_id
  )
  AND rowid <= :cursor
  AND created_at >= :start_datetime
  AND created_at <= :end_datetime
ORDER BY
  rowid DESC
LIMIT
  :limit;

-- name: DeleteOldApiLog :exec
DELETE FROM api_log
WHERE
  created_at <= :created_at_before;

-- name: CountAllApiLog :one
SELECT
  count(1) AS count
FROM
  api_log;

-- name: CountApiLogBefore :one
SELECT
  count(1) AS count
FROM
  api_log
WHERE
  created_at <= :created_at_before;
