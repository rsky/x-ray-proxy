-- name: GetAllApiTokens :many
SELECT
  *
FROM
  api_token;

-- name: SaveApiToken :exec
INSERT INTO
  api_token (member_id, token, updated_at, created_at)
VALUES
  (:member_id, :token, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (member_id) DO UPDATE
SET
  token = excluded.token,
  updated_at = CURRENT_TIMESTAMP;
