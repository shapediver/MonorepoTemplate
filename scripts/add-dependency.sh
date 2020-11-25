NAME1=$1
NAME2=$2
NAME2=${NAME2[@]/'@shapediver/'/''}

if [ -z "$NAME1" ]
then
    echo 'Please provide a valid name.'
    exit 1
fi

if [ -z "$NAME2" ]
then
    lerna add $NAME1
else
    lerna add $NAME1 'packages/'$NAME2
fi