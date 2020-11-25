import package_A from '@shapediver/package_A';

const package_B = (): string => {
  return 'What does package_A say? ' + package_A();
};

export default package_B;