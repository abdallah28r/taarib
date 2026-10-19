define e = Character("Eileen")
define m = Character("Mara")
default player_name = "Sam"

label start:
    scene black
    e "Welcome to the station, [player_name]."
    "The lights flicker twice."
    m "Did you hear that? {i}Something{/i} is moving."
    menu:
        "Open the door":
            jump open_door
        "Wait here":
            jump wait_here

label open_door:
    e "The door is \"locked\" from the inside."
    return

label wait_here:
    m "We wait. Then we run."
    $ renpy.notify(_("Saved"))
    return
