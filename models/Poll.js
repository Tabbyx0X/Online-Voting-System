const mongoose = require('mongoose');

const pollSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, 'Please provide poll title'],
    trim: true
  },
  description: {
    type: String,
    trim: true
  },
  question: {
    type: String,
    required: [true, 'Please provide poll question']
  },
  options: [{
    text: {
      type: String,
      required: true
    },
    votes: [{
      userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
      votedAt: { type: Date, default: Date.now }
    }]
  }],
  pollType: {
    type: String,
    enum: ['single', 'multiple'],
    default: 'single'
  },
  targetAudience: {
    department: String,
    year: String,
    semester: String,
    specificUsers: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }]
  },
  createdBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  startDate: {
    type: Date,
    default: Date.now
  },
  endDate: {
    type: Date,
    required: true
  },
  isActive: {
    type: Boolean,
    default: true
  },
  allowAnonymous: {
    type: Boolean,
    default: false
  },
  settings: {
    showResults: {
      type: String,
      enum: ['always', 'after_vote', 'after_end'],
      default: 'after_vote'
    },
    allowChangeVote: {
      type: Boolean,
      default: false
    }
  }
}, {
  timestamps: true
});

// Virtual for total votes
pollSchema.virtual('totalVotes').get(function() {
  return this.options.reduce((total, option) => total + option.votes.length, 0);
});

// Check if poll is expired
pollSchema.virtual('isExpired').get(function() {
  return new Date() > this.endDate;
});

// Check if user has voted
pollSchema.methods.hasUserVoted = function(userId) {
  return this.options.some(option => 
    option.votes.some(vote => vote.userId.toString() === userId.toString())
  );
};

// Get results
pollSchema.methods.getResults = function() {
  const totalVotes = this.totalVotes;
  return this.options.map(option => ({
    text: option.text,
    votes: option.votes.length,
    percentage: totalVotes > 0 ? ((option.votes.length / totalVotes) * 100).toFixed(2) : 0
  }));
};

module.exports = mongoose.model('Poll', pollSchema);
