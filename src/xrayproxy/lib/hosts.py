KCS_HOST_DATA = (
    ("w00g.kancolle-server.com", "総合"),
    ("w01y.kancolle-server.com", "横須賀鎮守府"),
    ("w02k.kancolle-server.com", "呉鎮守府"),
    ("w03s.kancolle-server.com", "佐世保鎮守府"),
    ("w04m.kancolle-server.com", "舞鶴鎮守府"),
    ("w05o.kancolle-server.com", "大湊警備府"),
    ("w06t.kancolle-server.com", "トラック泊地"),
    ("w07l.kancolle-server.com", "リンガ泊地"),
    ("w08r.kancolle-server.com", "ラバウル基地"),
    ("w09s.kancolle-server.com", "ショートランド泊地"),
    ("w10b.kancolle-server.com", "ブイン基地"),
    ("w11t.kancolle-server.com", "タウイタウイ泊地"),
    ("w12p.kancolle-server.com", "パラオ泊地"),
    ("w13b.kancolle-server.com", "ブルネイ泊地"),
    ("w14h.kancolle-server.com", "単冠湾泊地"),
    ("w15p.kancolle-server.com", "幌筵泊地"),
    ("w16s.kancolle-server.com", "宿毛湾泊地"),
    ("w17k.kancolle-server.com", "鹿屋基地"),
    ("w18i.kancolle-server.com", "岩川基地"),
    ("w19s.kancolle-server.com", "佐伯湾泊地"),
    ("w20h.kancolle-server.com", "柱島泊地"),
)


def get_kcs_hosts() -> tuple[str, ...]:
    return tuple(map(lambda x: x[0], KCS_HOST_DATA))


def get_kcs_host_names() -> tuple[str, ...]:
    return tuple(map(lambda x: x[1], KCS_HOST_DATA))


def get_kcs_host_dict() -> dict[str, str]:
    return dict(KCS_HOST_DATA)


def get_kcs_host_set() -> frozenset[str]:
    return frozenset(map(lambda x: x[0], KCS_HOST_DATA))
