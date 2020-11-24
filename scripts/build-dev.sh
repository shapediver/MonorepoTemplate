rm -rf ./dist-dev
mkdir dist-dev
cp index.html dist-dev/index.html 
webpack serve --config node_modules/@shapediver/webpack-config/webpack.prod.js --output-filename bundle.js --output-path dist-dev --content-base ./dist-dev