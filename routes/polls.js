const express = require('express');
const router = express.Router();
const Poll = require('../models/Poll');
const { asyncHandler } = require('../middleware/errorHandler');
const { isAuthenticated, authorize } = require('../middleware/auth');

// @route   POST /api/polls
// @desc    Create new poll
// @access  Private/Teacher/Admin
router.post('/', isAuthenticated, authorize('teacher', 'admin'), 
  asyncHandler(async (req, res) => {
  
  const { 
    title, 
    description, 
    question, 
    options, 
    pollType, 
    targetAudience,
    endDate,
    allowAnonymous,
    settings
  } = req.body;

  if (!options || options.length < 2) {
    return res.status(400).json({ 
      success: false, 
      error: 'Poll must have at least 2 options' 
    });
  }

  const poll = await Poll.create({
    title,
    description,
    question,
    options: options.map(opt => ({ text: opt, votes: [] })),
    pollType: pollType || 'single',
    targetAudience: targetAudience || {},
    createdBy: req.user._id,
    endDate: new Date(endDate),
    allowAnonymous: allowAnonymous || false,
    settings: settings || {}
  });

  res.status(201).json({ 
    success: true, 
    message: 'Poll created successfully', 
    data: poll 
  });
}));

// @route   GET /api/polls
// @desc    Get all polls
// @access  Private
router.get('/', isAuthenticated, 
  asyncHandler(async (req, res) => {
  
  const { page = 1, limit = 10, status, createdBy } = req.query;

  const query = {};

  // Filter by status
  if (status === 'active') {
    query.isActive = true;
    query.endDate = { $gt: new Date() };
  } else if (status === 'expired') {
    query.endDate = { $lte: new Date() };
  }

  // Filter by creator (for teachers to see their own polls)
  if (createdBy === 'me') {
    query.createdBy = req.user._id;
  }

  // Filter by target audience for students
  if (req.user.role === 'student') {
    query.$or = [
      { 'targetAudience.department': req.user.department },
      { 'targetAudience.specificUsers': req.user._id },
      { targetAudience: {} }
    ];
  }

  const polls = await Poll.find(query)
    .populate('createdBy', 'name email')
    .limit(limit * 1)
    .skip((page - 1) * limit)
    .sort({ createdAt: -1 });

  const count = await Poll.countDocuments(query);

  // Add voting status for each poll
  const pollsWithStatus = polls.map(poll => {
    const pollObj = poll.toObject({ virtuals: true });
    pollObj.hasVoted = poll.hasUserVoted(req.user._id);
    return pollObj;
  });

  res.json({
    success: true,
    data: pollsWithStatus,
    pagination: {
      total: count,
      page: parseInt(page),
      pages: Math.ceil(count / limit)
    }
  });
}));

// @route   GET /api/polls/:id
// @desc    Get single poll with results
// @access  Private
router.get('/:id', isAuthenticated, asyncHandler(async (req, res) => {
  const poll = await Poll.findById(req.params.id)
    .populate('createdBy', 'name email department');

  if (!poll) {
    return res.status(404).json({ 
      success: false, 
      error: 'Poll not found' 
    });
  }

  const hasVoted = poll.hasUserVoted(req.user._id);
  const isCreator = poll.createdBy._id.toString() === req.user._id.toString();
  const isExpired = poll.isExpired;

  // Determine if results should be shown
  let showResults = false;
  if (isCreator || req.user.role === 'admin') {
    showResults = true;
  } else if (poll.settings.showResults === 'always') {
    showResults = true;
  } else if (poll.settings.showResults === 'after_vote' && hasVoted) {
    showResults = true;
  } else if (poll.settings.showResults === 'after_end' && isExpired) {
    showResults = true;
  }

  const pollData = poll.toObject({ virtuals: true });
  pollData.hasVoted = hasVoted;
  pollData.canVote = !hasVoted && !isExpired && poll.isActive;
  pollData.results = showResults ? poll.getResults() : null;

  // Hide voter details if not creator/admin
  if (!isCreator && req.user.role !== 'admin') {
    pollData.options = pollData.options.map(opt => ({
      _id: opt._id,
      text: opt.text,
      votes: opt.votes.length
    }));
  }

  res.json({ 
    success: true, 
    data: pollData 
  });
}));

// @route   POST /api/polls/:id/vote
// @desc    Vote on a poll
// @access  Private/Student
router.post('/:id/vote', isAuthenticated, asyncHandler(async (req, res) => {
  const { optionIds } = req.body; // Array for multiple choice

  if (!optionIds || (Array.isArray(optionIds) && optionIds.length === 0)) {
    return res.status(400).json({ 
      success: false, 
      error: 'Please select at least one option' 
    });
  }

  const poll = await Poll.findById(req.params.id);

  if (!poll) {
    return res.status(404).json({ 
      success: false, 
      error: 'Poll not found' 
    });
  }

  // Check if poll is expired
  if (poll.isExpired) {
    return res.status(400).json({ 
      success: false, 
      error: 'This poll has ended' 
    });
  }

  // Check if poll is active
  if (!poll.isActive) {
    return res.status(400).json({ 
      success: false, 
      error: 'This poll is not active' 
    });
  }

  // Check if user already voted
  if (poll.hasUserVoted(req.user._id)) {
    if (!poll.settings.allowChangeVote) {
      return res.status(400).json({ 
        success: false, 
        error: 'You have already voted on this poll' 
      });
    }

    // Remove previous votes
    poll.options.forEach(option => {
      option.votes = option.votes.filter(
        vote => vote.userId.toString() !== req.user._id.toString()
      );
    });
  }

  // Validate option IDs
  const selectedOptions = Array.isArray(optionIds) ? optionIds : [optionIds];
  
  if (poll.pollType === 'single' && selectedOptions.length > 1) {
    return res.status(400).json({ 
      success: false, 
      error: 'You can only select one option for this poll' 
    });
  }

  // Add votes
  selectedOptions.forEach(optionId => {
    const option = poll.options.id(optionId);
    if (option) {
      option.votes.push({
        userId: req.user._id,
        votedAt: new Date()
      });
    }
  });

  await poll.save();

  res.json({ 
    success: true, 
    message: 'Vote recorded successfully',
    data: poll.getResults()
  });
}));

// @route   PUT /api/polls/:id
// @desc    Update poll
// @access  Private/Teacher/Admin
router.put('/:id', isAuthenticated, authorize('teacher', 'admin'), 
  asyncHandler(async (req, res) => {
  
  const poll = await Poll.findById(req.params.id);

  if (!poll) {
    return res.status(404).json({ 
      success: false, 
      error: 'Poll not found' 
    });
  }

  // Check ownership
  if (poll.createdBy.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
    return res.status(403).json({ 
      success: false, 
      error: 'Not authorized to update this poll' 
    });
  }

  // Don't allow editing if poll has votes
  if (poll.totalVotes > 0) {
    return res.status(400).json({ 
      success: false, 
      error: 'Cannot edit poll that already has votes' 
    });
  }

  const { title, description, question, endDate, isActive } = req.body;

  if (title) poll.title = title;
  if (description) poll.description = description;
  if (question) poll.question = question;
  if (endDate) poll.endDate = new Date(endDate);
  if (isActive !== undefined) poll.isActive = isActive;

  await poll.save();

  res.json({ 
    success: true, 
    message: 'Poll updated successfully',
    data: poll 
  });
}));

// @route   DELETE /api/polls/:id
// @desc    Delete poll
// @access  Private/Teacher/Admin
router.delete('/:id', isAuthenticated, authorize('teacher', 'admin'), 
  asyncHandler(async (req, res) => {
  
  const poll = await Poll.findById(req.params.id);

  if (!poll) {
    return res.status(404).json({ 
      success: false, 
      error: 'Poll not found' 
    });
  }

  // Check ownership
  if (poll.createdBy.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
    return res.status(403).json({ 
      success: false, 
      error: 'Not authorized to delete this poll' 
    });
  }

  await poll.deleteOne();

  res.json({ 
    success: true, 
    message: 'Poll deleted successfully' 
  });
}));

// @route   GET /api/polls/:id/results
// @desc    Get detailed poll results
// @access  Private/Teacher/Admin
router.get('/:id/results', isAuthenticated, authorize('teacher', 'admin'), 
  asyncHandler(async (req, res) => {
  
  const poll = await Poll.findById(req.params.id)
    .populate('createdBy', 'name email')
    .populate('options.votes.userId', 'name email department rollNumber');

  if (!poll) {
    return res.status(404).json({ 
      success: false, 
      error: 'Poll not found' 
    });
  }

  // Check ownership
  if (poll.createdBy._id.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
    return res.status(403).json({ 
      success: false, 
      error: 'Not authorized to view detailed results' 
    });
  }

  const results = poll.getResults();
  const detailedResults = poll.options.map(option => ({
    text: option.text,
    votes: option.votes.length,
    voters: option.votes.map(vote => ({
      user: vote.userId,
      votedAt: vote.votedAt
    }))
  }));

  res.json({
    success: true,
    data: {
      poll: {
        title: poll.title,
        question: poll.question,
        totalVotes: poll.totalVotes,
        isExpired: poll.isExpired
      },
      summary: results,
      detailed: detailedResults
    }
  });
}));

module.exports = router;
