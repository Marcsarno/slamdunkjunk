extends Node
## The game's song, one track that keeps playing across the splash, the clubhouse and the round (an
## autoload, so changing scenes never restarts it). Full volume in the menus, softer during play.
## On the web it starts with the first tap (browsers hold sound until then). On/off is remembered.

const SONG := "res://assets/music/brittanys_graveyard_shift.mp3"
const MENU_DB := -2.0
const PLAY_DB := -11.0
const SETTINGS := "user://settings.cfg"

var player := AudioStreamPlayer.new()
var on := true
var _target_db := MENU_DB
var _tween: Tween


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS) == OK:
		on = bool(cfg.get_value("audio", "music", true))
	player.stream = load(SONG)
	player.volume_db = MENU_DB
	add_child(player)


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
