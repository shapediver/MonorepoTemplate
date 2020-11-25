import package_a from '@shapediver/package_a';

const package_b = (): string => {
  return 'What does package_a say? ' + package_a();
};

export default package_b;