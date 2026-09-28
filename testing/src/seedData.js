/**
 * Seed data for Activity Registration & Group Formation System
 */

const SEED_STUDENTS = [
  { id: 'stu_01', name: 'Alex Rivera', email: 'alex.r@college.edu', major: 'Computer Science', year: 'Junior', avatar: 'AR' },
  { id: 'stu_02', name: 'Bianca Chen', email: 'bianca.c@college.edu', major: 'Data Science', year: 'Senior', avatar: 'BC' },
  { id: 'stu_03', name: 'Carlos Mendez', email: 'carlos.m@college.edu', major: 'Electrical Eng', year: 'Junior', avatar: 'CM' },
  { id: 'stu_04', name: 'Diana Prince', email: 'diana.p@college.edu', major: 'Mechanical Eng', year: 'Sophomore', avatar: 'DP' },
  { id: 'stu_05', name: 'Ethan Hunt', email: 'ethan.h@college.edu', major: 'Cybersecurity', year: 'Senior', avatar: 'EH' },
  { id: 'stu_06', name: 'Fiona Gallagher', email: 'fiona.g@college.edu', major: 'Design & UI/UX', year: 'Junior', avatar: 'FG' },
  { id: 'stu_07', name: 'George Clark', email: 'george.c@college.edu', major: 'Computer Science', year: 'Freshman', avatar: 'GC' },
  { id: 'stu_08', name: 'Hannah Abbott', email: 'hannah.a@college.edu', major: 'Bioinformatics', year: 'Senior', avatar: 'HA' },
  { id: 'stu_09', name: 'Ian Malcolm', email: 'ian.m@college.edu', major: 'Mathematics', year: 'Junior', avatar: 'IM' },
  { id: 'stu_10', name: 'Julia Roberts', email: 'julia.r@college.edu', major: 'Software Eng', year: 'Sophomore', avatar: 'JR' },
  { id: 'stu_11', name: 'Kevin Bacon', email: 'kevin.b@college.edu', major: 'Business & Tech', year: 'Senior', avatar: 'KB' },
  { id: 'stu_12', name: 'Laura Croft', email: 'laura.c@college.edu', major: 'Robotics', year: 'Junior', avatar: 'LC' },
  { id: 'stu_13', name: 'Marcus Vance', email: 'marcus.v@college.edu', major: 'Computer Science', year: 'Freshman', avatar: 'MV' },
  { id: 'stu_14', name: 'Nina Simone', email: 'nina.s@college.edu', major: 'Digital Art', year: 'Sophomore', avatar: 'NS' }
];

const SEED_PAST_ACTIVITIES = [
  {
    id: 'past_act_01',
    title: 'Spring 2026 Hackathon',
    date: '2026-03-15',
    groups: [
      { id: 'p_g1', members: ['stu_01', 'stu_02', 'stu_03'] },
      { id: 'p_g2', members: ['stu_04', 'stu_05', 'stu_06'] },
      { id: 'p_g3', members: ['stu_07', 'stu_08', 'stu_09'] }
    ]
  },
  {
    id: 'past_act_02',
    title: 'Winter Web Dev Sprint',
    date: '2026-01-20',
    groups: [
      { id: 'p_g4', members: ['stu_01', 'stu_04'] },
      { id: 'p_g5', members: ['stu_02', 'stu_05'] },
      { id: 'p_g6', members: ['stu_03', 'stu_06'] }
    ]
  }
];

const SEED_ACTIVITIES = [
  {
    id: 'act_101',
    title: 'AI Innovation Challenge 2026',
    description: 'Collaborative AI project challenge to build domain-specific AI agents and web apps using modern LLM frameworks.',
    category: 'Hackathon & Tech',
    activityDate: '2026-10-15T09:00',
    durationMinutes: 480,
    regDeadline: '2026-10-10T23:59',
    groupCutoffDate: '2026-10-11T12:00',
    groupSize: 3,
    status: 'OPEN',
    attachments: [
      { id: 'att_1', name: 'AI_Challenge_Guidelines.pdf', size: '2.4 MB', type: 'application/pdf', url: '#' },
      { id: 'att_2', name: 'Dataset_Sample.csv', size: '512 KB', type: 'text/csv', url: '#' },
      { id: 'att_3', name: 'Evaluation_Rubric.pdf', size: '1.1 MB', type: 'application/pdf', url: '#' }
    ],
    registrations: ['stu_01', 'stu_02', 'stu_03', 'stu_04', 'stu_05', 'stu_06', 'stu_07', 'stu_08', 'stu_09', 'stu_10']
  },
  {
    id: 'act_102',
    title: 'Autonomous Robotics Workshop',
    description: 'Hands-on hardware and control systems workshop to build and program micro-rovers.',
    category: 'Engineering & Hardware',
    activityDate: '2026-10-22T10:00',
    durationMinutes: 300,
    regDeadline: '2026-10-18T23:59',
    groupCutoffDate: '2026-10-19T17:00',
    groupSize: 4,
    status: 'OPEN',
    attachments: [
      { id: 'att_4', name: 'Rover_Assembly_Diagram.pdf', size: '4.8 MB', type: 'application/pdf', url: '#' }
    ],
    registrations: ['stu_01', 'stu_02', 'stu_03', 'stu_04', 'stu_05', 'stu_06', 'stu_07', 'stu_08', 'stu_11', 'stu_12', 'stu_13']
  },
  {
    id: 'act_103',
    title: 'UI/UX Design Jam',
    description: 'Design interactive web and mobile prototypes focusing on accessible campus navigation apps.',
    category: 'Design & Creative',
    activityDate: '2026-11-05T14:00',
    durationMinutes: 240,
    regDeadline: '2026-11-01T23:59',
    groupCutoffDate: '2026-11-02T12:00',
    groupSize: 2,
    status: 'OPEN',
    attachments: [
      { id: 'att_5', name: 'Design_System_Figma_Template.pdf', size: '3.1 MB', type: 'application/pdf', url: '#' }
    ],
    registrations: ['stu_06', 'stu_14']
  }
];

module.exports = {
  SEED_STUDENTS,
  SEED_PAST_ACTIVITIES,
  SEED_ACTIVITIES
};
