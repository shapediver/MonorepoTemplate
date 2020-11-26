rm -rf ./dist-prod
mkdir dist-prod
cp index.html dist-prod/index.html
SCOPE=$(json -f 'scope.json' scope)
webpack --config node_modules/@shapediver/$SCOPE.webpack-config/webpack.prod.js --output-filename bundle.js --output-path dist-prod