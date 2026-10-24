extends Node
## The game's songs, played one after another round and round, across the splash, the clubhouse and
## the round (an autoload, so changing scenes never restarts them). Full volume in the menus, softer
## during play. On the web it starts with the first tap (browsers hold sound until then). On/off is
## remembered.

const SONGS := [
	"res://assets/music/brittanys_graveyard_shift.mp3",
	"res://assets/music/bad_luck_on_the_back_nine.mp3",     # "Bad Luck on the Back Nine" (Marc's)
	"res://assets/music/stay_off_the_grass.mp3",            # "Stay Off the Grass" (Marc's), last before it starts over
]
const MENU_DB := -2.0
const PLAY_DB := -11.0
const SETTINGS := "user://settings.cfg"

var player := AudioStreamPlayer.new()
var on := true
var _song := 0
var _target_db := MENU_DB
var _tween: Tween


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS) == OK:
		on = bool(cfg.get_value("audio", "music", true))
	player.stream = _load(0)
	player.volume_db = MENU_DB
	player.finished.connect(_next)
	add_child(player)


## A song as it plays here: once through (the list does the looping).
func _load(i: int) -> AudioStream:
	var st: AudioStream = load(SONGS[i])
	if st is AudioStreamMP3:
		(st as AudioStreamMP3).loop = false
	return st


## One song ends: the next one starts, at whatever volume the menus or the round have set.
func _next() -> void:
	if not on:
		return
	_song = (_song + 1) % SONGS.size()
	player.stream = _load(_song)
	player.play()


## Start the song (if it isn't already playing and music is on).
func start() -> void:
	if on and not player.playing:
		player.volume_db = -40.0
		player.play()
		_fade_to(_target_db, 1.5)


## Menus (false) or play (true): the song sits further back while you play.
func set_in_play(playing: bool) -> void:
	_target_db = PLAY_DB if playing else MENU_DB
	if player.playing:
		_fade_to(_target_db, 1.0)


func toggle() -> bool:
	on = not on
	var cfg := ConfigFile.new()
	cfg.load(SETTINGS)
	cfg.set_value("audio", "music", on)
	cfg.save(SETTINGS)
	if on:
		start()
	else:
		player.stop()
	return on


func _fade_to(db: float, seconds: float) -> void:
	if _tween:
		_tween.kill()
	_tween = create_tween()
	_tween.tween_property(player, "volume_db", db, seconds)
