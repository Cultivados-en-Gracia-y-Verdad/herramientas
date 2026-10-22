import { migrate, openDatabase } from './db.js';
const db = openDatabase();
migrate(db);
db.close();
console.log('Database migrations applied.');
