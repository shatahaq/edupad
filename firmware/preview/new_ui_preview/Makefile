# Eksperimen layar bergaya Duolingo: `make` lalu buka out/*.gif (tema terang) dan
# out_dark/*.gif (tema gelap, biru malam; scene.cpp dengan -DNEW_UI_DARK=1).
# scene.cpp di folder ini menggantikan ../../edupad/scene.cpp (interface scene.h sama), jadi
# data layarnya sama dengan pratinjau biasa. Font dibuat dari ../../tools/fonts/Nunito.ttf.
LGFX ?= $(HOME)/Arduino/libraries/LovyanGFX/src
FW := ../../edupad
TOOLS := ../../tools
FLAGS := -O2 -DLGFX_LINUX_FB -I. -I$(LGFX) -I$(FW)
LIB_CPP := $(wildcard $(LGFX)/lgfx/v1/*.cpp)
LIB_C := $(wildcard $(LGFX)/lgfx/utility/*.c) $(shell find $(LGFX)/lgfx/Fonts -name '*.c')
LIB_OBJ := $(patsubst $(LGFX)/%,build/lib/%.o,$(LIB_CPP) $(LIB_C))
APP_OBJ := build/preview.o build/scene.o

all: out/boot.gif out_dark/boot.gif

out/boot.gif: build/preview ../make_gif.py
	mkdir -p out
	./build/preview out
	python3 ../make_gif.py out

out_dark/boot.gif: build/preview_dark ../make_gif.py
	mkdir -p out_dark
	./build/preview_dark out_dark
	python3 ../make_gif.py out_dark

build/preview: $(APP_OBJ) $(LIB_OBJ)
	g++ $^ -o $@ -lpthread

build/preview_dark: build/preview.o build/scene_dark.o $(LIB_OBJ)
	g++ $^ -o $@ -lpthread

new_ui_fonts.h: $(TOOLS)/make_font.py $(TOOLS)/fonts/Nunito.ttf
	python3 $(TOOLS)/make_font.py $(TOOLS)/fonts/Nunito.ttf $@ \
	    new_ui_logo=Black:58:EduPad new_ui_title=Black:30 new_ui_head=ExtraBold:23 \
	    new_ui_text=Bold:19 new_ui_small=Bold:15

build/lib/%.cpp.o: $(LGFX)/%.cpp
	@mkdir -p $(dir $@)
	g++ -std=c++17 $(FLAGS) -c $< -o $@

build/lib/%.c.o: $(LGFX)/%.c
	@mkdir -p $(dir $@)
	gcc $(FLAGS) -c $< -o $@

build/preview.o: preview.cpp $(FW)/earcon.h $(FW)/sound_cues.h $(FW)/config.h $(FW)/scene.h
	@mkdir -p build
	g++ -std=c++17 $(FLAGS) -c $< -o $@

build/scene.o: scene.cpp new_ui_fonts.h $(FW)/scene.h $(FW)/owl_sprites.h
	@mkdir -p build
	g++ -std=c++17 -Wall $(FLAGS) -c $< -o $@

# Video bersuara: `make video` -> out/<layar>.mp4 + out/demo.mp4 (semua layar berurutan) beserta
# GIF/PNG-nya, juga di out_dark/. Efek suara: $(FW)/earcon.h + $(FW)/sound_cues.h (sama dengan
# firmware) dan out/sounds.wav berisi semua bunyi. Suara TTS asli (perkenalan + jawaban)
# dari $(VOICE)/, dibuat sekali dengan `python make_voice.py` (butuh paket edupad + .env di root
# repo). Tanpa $(VOICE)/ hanya efek suara. Butuh ffmpeg.
VOICE ?= voice
video: build/preview build/preview_dark make_video.py ../make_gif.py
	mkdir -p out out_dark
	./build/preview out $(VOICE)
	python3 make_video.py out
	python3 ../make_gif.py out
	./build/preview_dark out_dark $(VOICE)
	python3 make_video.py out_dark
	python3 ../make_gif.py out_dark

build/scene_dark.o: scene.cpp new_ui_fonts.h $(FW)/scene.h $(FW)/owl_sprites.h
	@mkdir -p build
	g++ -std=c++17 -Wall -DNEW_UI_DARK=1 $(FLAGS) -c $< -o $@

clean:
	rm -rf build out out_dark

.PHONY: all clean video
