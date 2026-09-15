[
  "import React from 'react';\n\ninterface Props {\n  stats: any;\n}\n\nconst DashboardStats: React.FC<Props> = ({ stats }) => {\n  return (\n    <div>\n      <h1>Dashboard Stats</h1>\n      <p>Patients: {stats.patients}</p>\n      <p>Doctors: {stats.doctors}</p>\n      <p>Appointments: {stats.appointments}</p>\n    </div>\n  );\n};\n\nexport default DashboardStats;"
]