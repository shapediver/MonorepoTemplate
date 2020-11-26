rm -rf ./dist-dev
mkdir dist-dev
cp index.html dist-dev/index.html 
SCOPE=$(json -f 'scope.json' scope)
webpack serve --config node_modules/@shapediver/$SCOPE.webpack-config/webpack.prod.js --output-filename bundle.js --output-path dist-dev --content-base ./dist-dev