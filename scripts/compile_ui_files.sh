#!/bin/bash

ui_source=./empkins_sync_board_gui/ui/
ui_dest=./empkins_sync_board_gui/components/
rc_dest=./empkins_sync_board_gui/

for f in $(find $ui_source -name *.ui)
do
		basepath=${f##*/}
		py_file=${basepath%.ui}.py
		output="${ui_dest}${py_file}"
		pyside2-uic $f -o $output
		echo "Finished: ${output}"
done

for f in $(find $ui_source -name *.qrc)
do
		basepath=${f##*/}
		py_file=${basepath%.qrc}_rc.py
		output="${py_file}"
		pyside2-rcc $f -o $output
		echo "Finished: ${output}"
done
