-- api_mst_ship
CREATE TABLE IF NOT EXISTS ship (
  id INTEGER NOT NULL, -- api_id
  sort_id INTEGER NOT NULL, -- api_sort_id
  name TEXT NOT NULL, -- api_name
  yomi TEXT NOT NULL, -- api_yomi
  ship_type_id INTEGER, -- api_stype
  picture_book_no INTEGER, -- api_sortno,
  after_lv INTEGER, -- api_afterlv
  after_ship_id INTEGER, -- api_aftershipid
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_ship_sort_id ON ship (sort_id);

CREATE INDEX IF NOT EXISTS idx_ship_name ON ship (name);

CREATE INDEX IF NOT EXISTS idx_ship_picture_book_no ON ship (picture_book_no);

-- api_mst_shipgraph + image sizes
CREATE TABLE IF NOT EXISTS shipgraph (
  host TEXT NOT NULL, -- host address
  ship_id INTEGER NOT NULL, -- api_id
  version INTEGER NOT NULL, -- api_version[0]
  filename TEXT NOT NULL, -- api_filename
  full_width INTEGER, -- width of the full ship image
  full_height INTEGER, -- height of the full ship image
  full_dmg_width INTEGER, -- width of the full damaged ship image
  full_dmg_height INTEGER, -- height of the full damaged ship image
  points TEXT NOT NULL DEFAULT '{}', -- JSON {"battle_n": [x, y], "battle_d": [x,y], ...}
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (host, ship_id, version)
);

CREATE INDEX IF NOT EXISTS idx_shipgraph_ship_id_latest ON shipgraph (ship_id ASC, version DESC, updated_at DESC);

-- log for api requests and responses
CREATE TABLE IF NOT EXISTS api_log (
  bucket TEXT NOT NULL,
  object_key TEXT NOT NULL,
  member_id INTEGER,
  host TEXT NOT NULL,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  params TEXT, -- JSON
  raw_size INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  rowid INTEGER PRIMARY KEY -- for sqlc
);

CREATE INDEX IF NOT EXISTS idx_api_log_created_at ON api_log (created_at);

CREATE INDEX IF NOT EXISTS idx_api_log_member_id_created_at ON api_log (member_id, created_at);

CREATE INDEX IF NOT EXISTS idx_api_log_member_id_path_created_at ON api_log (member_id, path, created_at);

CREATE INDEX IF NOT EXISTS idx_api_log_path_created_at ON api_log (path, created_at);

-- map of member_id and api_token
CREATE TABLE IF NOT EXISTS api_token (
  member_id INTEGER NOT NULL,
  token TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (member_id),
  UNIQUE (token)
);
