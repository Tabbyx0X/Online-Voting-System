const mongoose = require('mongoose');

const assignmentSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, 'Please provide assignment title'],
    trim: true
  },
  description: {
    type: String,
    required: [true, 'Please provide assignment description']
  },
  subject: {
    type: String,
    required: true
  },
  department: String,
  year: String,
  semester: String,
  createdBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  dueDate: {
    type: Date,
    required: true
  },
  totalMarks: {
    type: Number,
    default: 100
  },
  attachments: [{
    filename: String,
    url: String,
    uploadedAt: Date
  }],
  submissions: [{
    studentId: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
    submittedAt: Date,
    files: [String],
    marks: Number,
    feedback: String,
    status: { type: String, enum: ['pending', 'reviewed', 'graded'], default: 'pending' }
  }],
  isActive: {
    type: Boolean,
    default: true
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Assignment', assignmentSchema);
