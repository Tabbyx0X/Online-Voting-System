const express = require('express');
const router = express.Router();
const User = require('../models/User');
const { asyncHandler } = require('../middleware/errorHandler');
const { isAuthenticated, authorize } = require('../middleware/auth');

// @route   GET /api/users
// @desc    Get all users (admin can see all colleges)
// @access  Private/Admin
router.get('/', isAuthenticated, authorize('admin', 'teacher'), 
  asyncHandler(async (req, res) => {
  
  const { page = 1, limit = 20, search, role, department, isActive } = req.query;

  const query = {};

  if (search) {
    query.$or = [
      { name: { $regex: search, $options: 'i' } },
      { email: { $regex: search, $options: 'i' } },
      { rollNumber: { $regex: search, $options: 'i' } }
    ];
  }
  if (role) query.role = role;
  if (department) query.department = department;
  if (isActive !== undefined) query.isActive = isActive === 'true';

  const users = await User.find(query)
    .select('-password')
    .limit(limit * 1)
    .skip((page - 1) * limit)
    .sort({ createdAt: -1 });

  const count = await User.countDocuments(query);

  res.json({
    success: true,
    data: users,
    pagination: {
      total: count,
      page: parseInt(page),
      pages: Math.ceil(count / limit)
    }
  });
}));

// @route   GET /api/users/:id
// @desc    Get user by ID
// @access  Private
router.get('/:id', isAuthenticated, asyncHandler(async (req, res) => {
  const user = await User.findById(req.params.id)
    .select('-password');

  if (!user) {
    return res.status(404).json({ 
      success: false, 
      error: 'User not found' 
    });
  }

  // Check if user can access this profile
  if (req.user.role !== 'admin' && 
      req.user._id.toString() !== user._id.toString()) {
    return res.status(403).json({ 
      success: false, 
      error: 'Not authorized to access this profile' 
    });
  }

  res.json({ 
    success: true, 
    data: user 
  });
}));

// @route   PUT /api/users/:id
// @desc    Update user (Admin only)
// @access  Private/Admin
router.put('/:id', isAuthenticated, authorize('admin'), 
  asyncHandler(async (req, res) => {
  
  const { role, department, isActive, rollNumber } = req.body;

  const user = await User.findById(req.params.id);

  if (!user) {
    return res.status(404).json({ 
      success: false, 
      error: 'User not found' 
    });
  }

  // Admin can update any user
  if (role) user.role = role;
  if (department) user.department = department;
  if (isActive !== undefined) user.isActive = isActive;
  if (rollNumber) user.rollNumber = rollNumber;

  await user.save();

  res.json({ 
    success: true, 
    message: 'User updated successfully',
    data: user 
  });
}));

// @route   DELETE /api/users/:id
// @desc    Delete user (Soft delete)
// @access  Private/Admin
router.delete('/:id', isAuthenticated, authorize('admin'), 
  asyncHandler(async (req, res) => {
  
  const user = await User.findById(req.params.id);

  if (!user) {
    return res.status(404).json({ 
      success: false, 
      error: 'User not found' 
    });
  }

  // Admin can delete any user
  user.isActive = false;
  await user.save();

  res.json({ 
    success: true, 
    message: 'User deactivated successfully' 
  });
}));

module.exports = router;
