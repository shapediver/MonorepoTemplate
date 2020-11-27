rm -rf ./dist-prod
mkdir dist-prod
cp index.html dist-prod/index.html
webpack --config ../../webpack.prod.js --output-filename bundle.js --output-path dist-prod