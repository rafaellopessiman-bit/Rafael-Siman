import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import {
  Conversation,
  ConversationDocument,
} from './conversation.schema';
import {
  IConversationRepository,
  CreateConversationData,
  AppendMessageData,
} from '../../domain/repositories/conversation.repository.interface';

@Injectable()
export class MongooseConversationRepository implements IConversationRepository {
  constructor(
    @InjectModel(Conversation.name)
    private readonly model: Model<ConversationDocument>,
  ) {}

  async create(data: CreateConversationData): Promise<ConversationDocument> {
    return this.model.create({
      ...data,
      messages: [],
      totalTokens: 0,
      messageCount: 0,
      isActive: true,
      schemaVersion: 1,
    });
  }

  async findById(id: string): Promise<ConversationDocument | null> {
    return this.model.findById(id);
  }

  async findAll(onlyActive = true): Promise<ConversationDocument[]> {
    const filter = onlyActive ? { isActive: true } : {};
    return this.model
      .find(filter)
      .sort({ updatedAt: -1 })
      .select('-messages');
  }

  async findPaginated(skip: number, limit: number, onlyActive = true): Promise<ConversationDocument[]> {
    const filter = onlyActive ? { isActive: true } : {};
    return this.model
      .find(filter)
      .sort({ updatedAt: -1 })
      .skip(skip)
      .limit(limit)
      .select('-messages');
  }

  async countAll(onlyActive = true): Promise<number> {
    const filter = onlyActive ? { isActive: true } : {};
    return this.model.countDocuments(filter);
  }

  async appendMessage(
    conversationId: string,
    message: AppendMessageData,
  ): Promise<ConversationDocument | null> {
    return this.model.findByIdAndUpdate(
      conversationId,
      {
        $push: {
          messages: { ...message, timestamp: new Date() },
        },
        $inc: { messageCount: 1 },
        $set: { updatedAt: new Date() },
      },
      { new: true },
    );
  }

  async addTokens(conversationId: string, tokens: number): Promise<void> {
    await this.model.updateOne(
      { _id: conversationId },
      { $inc: { totalTokens: tokens } },
    );
  }

  async archive(conversationId: string): Promise<void> {
    await this.model.updateOne(
      { _id: conversationId },
      { $set: { isActive: false, updatedAt: new Date() } },
    );
  }
}
