-- name: GetShip :one
SELECT
  *
FROM
  ship
WHERE
  id = :id
LIMIT
  1;

-- name: GetShipByPictureBookNo :one
SELECT
  *
FROM
  ship
WHERE
  picture_book_no = :picture_book_no
LIMIT
  1;

-- name: ListShipByName :many
SELECT
  *
FROM
  ship
WHERE
  name like :name_prefix || '%'
ORDER BY
  sort_id,
  id;

-- name: SaveShip :exec
INSERT INTO
  ship (
    id,
    sort_id,
    name,
    yomi,
    after_lv,
    ship_type_id,
    picture_book_no,
    after_ship_id,
    updated_at,
    created_at
  )
VALUES
  (
    :id,
    :sort_id,
    :name,
    :yomi,
    :after_lv,
    :ship_type_id,
    :picture_book_no,
    :after_ship_id,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
  )
ON CONFLICT (id) DO UPDATE
SET
  sort_id = excluded.sort_id,
  name = excluded.name,
  yomi = excluded.yomi,
  after_lv = excluded.after_lv,
  ship_type_id = excluded.ship_type_id,
  picture_book_no = excluded.picture_book_no,
  after_ship_id = excluded.after_ship_id,
  updated_at = CURRENT_TIMESTAMP;

-- name: GetLatestShipgraph :one
SELECT
  *
FROM
  shipgraph
WHERE
  ship_id = :ship_id
ORDER BY
  version DESC,
  updated_at DESC
LIMIT
  1;

-- name: GetLatestShipgraphByHost :one
SELECT
  *
FROM
  shipgraph
WHERE
  host = :host
  AND ship_id = :ship_id
ORDER BY
  version DESC,
  updated_at DESC
LIMIT
  1;

-- name: GetShipgraph :one
SELECT
  *
FROM
  shipgraph
WHERE
  host = :host
  AND ship_id = :ship_id
  AND version = :version
LIMIT
  1;

-- name: SaveShipgraph :exec
INSERT INTO
  shipgraph (
    host,
    ship_id,
    version,
    filename,
    points,
    updated_at,
    created_at
  )
VALUES
  (
    :host,
    :ship_id,
    :version,
    :filename,
    :points,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
  )
ON CONFLICT (host, ship_id, version) DO UPDATE
SET
  filename = excluded.filename,
  points = excluded.points,
  updated_at = CURRENT_TIMESTAMP;

-- name: SetShipgraphSize :exec
UPDATE shipgraph
SET
  full_width = :full_width,
  full_height = :full_height,
  updated_at = CURRENT_TIMESTAMP
WHERE
  host = :host
  AND ship_id = :ship_id
  AND version = :version;

-- name: SetShipgraphDamagedSize :exec
UPDATE shipgraph
SET
  full_dmg_width = :full_dmg_width,
  full_dmg_height = :full_dmg_height,
  updated_at = CURRENT_TIMESTAMP
WHERE
  host = :host
  AND ship_id = :ship_id
  AND version = :version;
