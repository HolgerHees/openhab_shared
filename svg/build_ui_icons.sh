#/bin/sh

DIRNAME=`dirname "$0"`

cd $DIRNAME

#rm build/png/*.png
#rm svg.optimized/*.svg
rm ../conf/icons/classic/*.png
#rm ../conf/icons/classic/*.svg

mogrify -background "#00000000" -path ../conf/icons/classic/ -format png classic/*.svg

#npm install -g svgo
#svgo svg/*.svg -o svg.optimized/

#cp build/png/*.png ../conf/icons/classic/
#cp svg/*.svg ../conf/icons/classic/
#cp svg.optimized/*.svg ../../conf/icons/classic/

