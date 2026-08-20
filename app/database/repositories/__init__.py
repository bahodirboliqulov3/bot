from .base_repo import BaseRepository
from .user_repo import UserRepository, AdminRepository
from .group_repo import GroupRepository
from .test_repo import TestRepository, SubjectRepository, TopicRepository
from .result_repo import ResultRepository, AttemptRepository, AchievementRepository
from .certificate_repo import CertificateRepository
from .support_repo import SupportRepository
from .channel_repo import ChannelRepository
from .stats_repo import StatsRepository

all = [
    "BaseRepository",
    "UserRepository",
    "AdminRepository",
    "GroupRepository",
    "TestRepository",
    "SubjectRepository",
    "TopicRepository",
    "ResultRepository",
    "AttemptRepository",
    "AchievementRepository",
    "CertificateRepository",
    "SupportRepository",
    "ChannelRepository",
    "StatsRepository",
]
