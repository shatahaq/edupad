# Pratinjau layar di PC (Linux) tanpa LCD maupun SDL: `make` lalu buka out/*.gif.
LGFX ?= $(HOME)/Arduino/libraries/LovyanGFX/src
FW := ../edupad
FLAGS := -O2 -DLGFX_LINUX_FB -I$(LGFX) -I$(FW)
LIB_CPP := $(wildcard $(LGFX)/lgfx/v1/*.cpp)
LIB_C := $(wildcard $(LGFX)/lgfx/utility/*.c) $(shell find $(LGFX)/lgfx/Fonts -name '*.c')
LIB_OBJ := $(patsubst $(LGFX)/%,build/lib/%.o,$(LIB_CPP) $(LIB_C))
APP_OBJ := build/preview.o build/scene.o

out/boot.gif: build/preview make_gif.py
	mkdir -p out
	./build/preview out
	python3 make_gif.py out

build/preview: $(APP_OBJ) $(LIB_OBJ)
	g++ $^ -o $@ -lpthread

build/lib/%.cpp.o: $(LGFX)/%.cpp
	@mkdir -p $(dir $@)
	g++ -std=c++17 $(FLAGS) -c $< -o $@

build/lib/%.c.o: $(LGFX)/%.c
	@mkdir -p $(dir $@)
	gcc $(FLAGS) -c $< -o $@

build/preview.o: preview.cpp $(FW)/scene.h
	@mkdir -p build
	g++ -std=c++17 $(FLAGS) -c $< -o $@

build/scene.o: $(FW)/scene.cpp $(FW)/scene.h $(FW)/owl_sprites.h $(FW)/ui_fonts.h
	@mkdir -p build
	g++ -std=c++17 -Wall $(FLAGS) -c $< -o $@

clean:
	rm -rf build out

.PHONY: clean
