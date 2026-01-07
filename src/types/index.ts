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
  info: string;
  tweet_count: number;
  stance_matrix: [number, number, number][]; // 简化的类型定义
  influence_type: { name: string; value: number }[];
  // 【新增】该用户当天的代表推文
  tweets: TweetItem[]; 
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


export interface TargetMetrics {
  bio: string;
  daily_count: number;
  keywords: string[];
  // active_hours 已移除
}

export interface TargetProfile {
  id: string;
  name: string;
  username: string;
  category: 'politician' | 'media';
  metrics: TargetMetrics;
  stance_matrix: [number, number, number][]; 
  influence_type: { name: string; value: number }[];
  
  // 【新增】该目标的推文列表 (用于前端按日期筛选)
  tweets: TweetItem[];
}

export interface DetectData {
  region: string;
  targets: TargetProfile[];
}