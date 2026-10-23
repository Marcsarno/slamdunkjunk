extends Node
## Sound effects (synthesized by tools/make_sfx.py), on a small pool of players so they can overlap.
## An autoload: Sfx.play("splash").

const DIR := "res://assets/sfx/"

var _streams := {}
var _players: Array[AudioStreamPlayer] = []
var _next := 0


func _ready() -> void:
	for i in 8:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)


## Load every sound now (behind the title card), so none is read from the pack mid-shot.
func preload_all() -> void:
	for f in DirAccess.get_files_at(DIR):
		var name := f.trim_suffix(".import").get_basename()
		if not _streams.has(name) and ResourceLoader.exists(DIR + name + ".wav"):
			_streams[name] = load(DIR + name + ".wav")


func play(name: String, volume_db := 0.0, pitch := 1.0) -> void:
	if not _streams.has(name):
		var path := DIR + name + ".wav"
		if not ResourceLoader.exists(path):
			return
		_streams[name] = load(path)
	var p := _players[_next]
	_next = (_next + 1) % _players.size()
	p.stream = _streams[name]
	p.volume_db = volume_db
	p.pitch_scale = pitch
	p.play()


## The same, a little later (thunder after its flash, the chime after the ball drops).
func play_after(seconds: float, name: String, volume_db := 0.0, pitch := 1.0) -> void:
	get_tree().create_timer(seconds).timeout.connect(func(): play(name, volume_db, pitch))
