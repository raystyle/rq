-- phpMyAdmin SQL Dump
-- version 3.1.1
-- http://www.phpmyadmin.net
--
-- Host: localhost
-- Generation Time: Mar 03, 2009 at 03:59 PM
-- Server version: 5.0.58
-- PHP Version: 5.2.6

SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";

--
-- Database: `rqp`
--

-- --------------------------------------------------------

--
-- Table structure for table `files`
--

DROP TABLE IF EXISTS `files`;
CREATE TABLE `files` (
  `f_id` INT NOT NULL auto_increment,
  `p_record` INT NOT NULL,
  `t_record` INT NOT NULL,
  `u_record` INT NOT NULL,
  `g_record` INT NOT NULL,
  `files` text NOT NULL,
  `f_is_suid` tinyint DEFAULT 0,
  `f_is_sgid` tinyint DEFAULT 0,
  `f_perms` varchar(4) NOT NULL,
  PRIMARY KEY  (`f_id`),
  KEY `rec` USING BTREE (`p_record`),
  KEY `trec` USING BTREE (`t_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1 ;

-- --------------------------------------------------------

--
-- Table structure for table `user_names`
--

DROP TABLE IF EXISTS `user_names`;
CREATE TABLE IF NOT EXISTS `user_names` (
  `u_record` INT NOT NULL auto_increment,
  `f_user` varchar(16) NOT NULL,
  PRIMARY KEY (`u_record`),
  KEY `rec` USING BTREE (`u_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `user_names`
--

DROP TABLE IF EXISTS `group_names`;
CREATE TABLE IF NOT EXISTS `group_names` (
  `g_record` INT NOT NULL auto_increment,
  `f_group` varchar(16) NOT NULL,
  PRIMARY KEY (`g_record`),
  KEY `rec` USING BTREE (`g_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `packages`
--

DROP TABLE IF EXISTS `packages`;
CREATE TABLE IF NOT EXISTS `packages` (
  `p_record` INT NOT NULL auto_increment,
  `t_record` INT NOT NULL,
  `p_tag` text NOT NULL,
  `p_package` text NOT NULL,
  `p_version` text NOT NULL,
  `p_release` text NOT NULL,
  `p_date` text NOT NULL,
  `p_arch` varchar(10) NOT NULL,
  `p_srpm` text NOT NULL,
  `p_fullname` text NOT NULL,
  `p_update` tinyint DEFAULT 0,
  PRIMARY KEY  (`p_record`),
  KEY `trec` USING BTREE (`t_record`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `provides`
--

DROP TABLE IF EXISTS `provides`;
CREATE TABLE IF NOT EXISTS `provides` (
  `p_id` INT NOT NULL auto_increment,
  `p_record` INT NOT NULL,
  `t_record` INT NOT NULL,
  `pv_record` INT NOT NULL,
  PRIMARY KEY  (`p_id`),
  KEY `rec` USING BTREE (`p_record`),
  KEY `trec` USING BTREE (`t_record`),
  KEY `pvrec` USING BTREE (`pv_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `provides_names`
--

DROP TABLE IF EXISTS `provides_names`;
CREATE TABLE IF NOT EXISTS `provides_names` (
  `pv_record` INT NOT NULL auto_increment,
  `pv_name` text NOT NULL,
  PRIMARY KEY (`pv_record`),
  KEY `rec` USING BTREE (`pv_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `requires`
--

DROP TABLE IF EXISTS `requires`;
CREATE TABLE IF NOT EXISTS `requires` (
  `r_id` INT NOT NULL auto_increment,
  `p_record` INT NOT NULL,
  `t_record` INT NOT NULL,
  `rq_record` INT NOT NULL,
  PRIMARY KEY  (`r_id`),
  KEY `rec` USING BTREE (`p_record`),
  KEY `trec` USING BTREE (`t_record`),
  KEY `rqrec` USING BTREE (`rq_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `requires_names`
--

DROP TABLE IF EXISTS `requires_names`;
CREATE TABLE IF NOT EXISTS `requires_names` (
  `rq_record` INT NOT NULL auto_increment,
  `rq_name` text NOT NULL,
  PRIMARY KEY (`rq_record`),
  KEY `rec` USING BTREE (`rq_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `symbols`
--

DROP TABLE IF EXISTS `symbols`;
CREATE TABLE IF NOT EXISTS `symbols` (
  `s_id` INT NOT NULL auto_increment,
  `p_record` INT NOT NULL,
  `t_record` INT NOT NULL,
  `f_id` INT NOT NULL,
  `symbols` text NOT NULL,
  PRIMARY KEY  (`s_id`),
  KEY `rec` USING BTREE (`p_record`),
  KEY `trec` USING BTREE (`t_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `flags`
--

DROP TABLE IF EXISTS `flags`;
CREATE TABLE IF NOT EXISTS `flags` (
  `l_id` INT NOT NULL auto_increment,
  `p_record` INT NOT NULL,
  `t_record` INT NOT NULL,
  `f_id` INT NOT NULL,
  `f_relro` tinyint DEFAULT 0,
  `f_ssp` tinyint DEFAULT 0,
  `f_pie` tinyint DEFAULT 0,
  `f_fortify` tinyint DEFAULT 0,
  `f_nx` tinyint DEFAULT 0,
  PRIMARY KEY  (`l_id`),
  KEY `rec` USING BTREE (`p_record`),
  KEY `trec` USING BTREE (`t_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `tags`
--

DROP TABLE IF EXISTS `tags`;
CREATE TABLE IF NOT EXISTS `tags` (
  `t_record` INT NOT NULL auto_increment,
  `tag` varchar(128) NOT NULL,
  `path` varchar(256) NOT NULL,
  `tdate` varchar(26) NOT NULL,
  `update_path` varchar(256) NOT NULL,
  `update_date` varchar(26),
  PRIMARY KEY  (`t_record`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `alreadyseen`
--

DROP TABLE IF EXISTS `alreadyseen`;
CREATE TABLE IF NOT EXISTS `alreadyseen` (
  `a_record` INT NOT NULL auto_increment,
  `p_fullname` text NOT NULL,
  `t_record` INT NOT NULL,
  PRIMARY KEY  (`a_record`),
  KEY `trec` USING BTREE (`t_record`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;
