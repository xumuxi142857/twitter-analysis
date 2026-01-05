// src/types/index.ts
export interface TopicStance {
  topic: string;
  stance: 'positive' | 'neutral' | 'negative';
}

export interface WordCloudItem {
  name: string;
  value: number;
}

// 这是页面主要的数据对象
export interface RegionData {
  time_range: [string, string];
  top_topics: TopicStance[];
  hot_words: WordCloudItem[];
}

// src/types/index.ts (追加)

// 1. 影响类型 (饼图数据)
export interface InfluenceType {
  name: '亲情 (Kinship)' | '同伴 (Peer)' | '权威 (Authority)';
  value: number; // 占比或得分
}

// 2. 立场矩阵 (热力图数据)
// 结构: [X轴索引, Y轴索引, 值]
// X轴: [0:反华/负面, 1:中立, 2:亲华/正面]
// Y轴: [0:政治, 1:军事, 2:经济, 3:文化]
export type StanceMatrixItem = [number, number, number]; 

// 3. 用户画像详情
export interface UserProfile {
  username: string;
  info: string; // 用户简介/摘要
  tweet_count: number; // 活跃度
  stance_matrix: StanceMatrixItem[]; // 矩阵数据
  influence_type: InfluenceType[]; // 饼图数据
}

// 4. 页面总数据结构
export interface AccountAnalysisData {
  region: string;
  time_range: [string, string];
  top_users: UserProfile[];
}



// src/types/index.ts (追加)

// 引导草稿内容
export interface GuideDrafts {
  authority: string; // 权威 (官方/严肃)
  peer: string;      // 同伴 (网友/幽默/共情)
  kinship: string;   // 亲情 (感性/家庭/温暖)
}

// 引导模块的话题项
export interface GuideTopicItem {
  topic: string;
  stance: 'positive' | 'neutral' | 'negative';
  drafts: GuideDrafts; // 包含三种草稿
}

// 引导模块总数据
export interface GuideData {
  region: string;
  time_range: [string, string];
  topics: GuideTopicItem[];
}


// src/types/index.ts (追加)

// 目标人物的基本指标
export interface TargetMetrics {
  bio: string;          // 人设/简介 (LLM生成)
  daily_count: number;  // 日均发稿量 (Python计算)
  keywords: string[];   // 核心关键词 (LLM提取)
  active_hours: string; // 活跃时段 (如 "19:00 - 23:00")
}

// 目标人物详情
export interface TargetProfile {
  id: string;
  name: string;        // 显示名 (如 Elon Musk)
  username: string;    // 推特handle (如 elonmusk)
  category: 'politician' | 'media'; // 类别
  avatar_url?: string; // 头像链接 (可选)
  metrics: TargetMetrics;
  
  // 复用之前的图表数据结构
  stance_matrix: StanceMatrixItem[]; 
  influence_type: InfluenceType[];
}

// 页面总数据
export interface DetectData {
  region: string;
  time_range: [string, string];
  targets: TargetProfile[];
}


// src/types/index.ts

export interface TweetItem {
  text: string;
  stance: 'positive' | 'neutral' | 'negative';
  // 新增元数据字段
  username: string;
  created_at: string;
  metrics: {
    reply: number;
    retweet: number;
    like: number;
  };
}

export interface TopicCluster {
  topic: string;
  tweets: TweetItem[];
}

export interface WordCloudItem {
  name: string;
  value: number;
}

export interface RegionAnalysisData {
  region: string;
  time_range: [string, string];
  top_topics: TopicCluster[];
  hot_words: WordCloudItem[];
}